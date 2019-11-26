#!/usr/bin/env python3
'''
Fear and Terror's bot for party matchmaking on Discord
'''
import discord
import os
from discord.utils import get
from discord.ext import commands
from config import *
import jsonpickle
from random import randint

DATABASE_FILENAME = "database.json"

bot = commands.Bot(command_prefix=BOT_CMD_PREFIX)

###############################################################################
## Bot commands
###############################################################################
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def startparty(ctx):
    check_channel(ctx.channel)
    if await get_active_party(ctx.channel) is not None:
        raise PartyAlreadyStartedError()

    db = read_database()
    subscriber_role = db[ctx.channel.id].get_subscriber_role(ctx.guild)
    party = Party(ctx.channel, ctx.author, db[ctx.channel.id].max_slots - 1)
    message = await ctx.send(f"{subscriber_role.mention} {ctx.author.mention}",
                             embed=party.to_embed())
    db[ctx.channel.id].set_current_party_message(message)
    save_database(db)
    await message.add_reaction(BOT_JOIN_EMOJI)


@startparty.error
async def startparty_error(ctx, error):
    error_handlers = {
        PartyAlreadyStartedError: lambda:
        ctx.send("A party has already been launched in this channel. " +
                 "Join that one or wait before creating another one.")
    }
    error_handlers.update(get_default_error_handlers(ctx, "startparty", ""))
    await handle_error(ctx, error, error_handlers)


@bot.command()
async def closeparty(ctx):
    check_channel(ctx.channel)
    party_message = await get_active_party(ctx.channel)
    if party_message is None:
        raise NoActivePartyError()
    admin_role = ctx.guild.get_role(BOT_ADMIN_ROLE)
    if party_message.author != ctx.author\
            and admin_role not in ctx.author.roles:
        raise commands.MissingRole()

    await ctx.send(f"> {ctx.author.mention} has just disbanded the party!\n"
                   f"> Type {BOT_CMD_PREFIX}startparty to launch a new party.")
    await party_message.delete()
    db = read_database()
    db[ctx.channel.id].unset_current_party_message()
    save_database(db)


@closeparty.error
async def closeparty_error(ctx, error):
    error_handlers = {
        NoActivePartyError: lambda:
        ctx.send("There is no active party in this channel.")
    }
    error_handlers.update(get_default_error_handlers(ctx, "closeparty", ""))
    await handle_error(ctx, error, error_handlers)


@bot.command()
@commands.has_role(BOT_ADMIN_ROLE)
async def activatechannel(ctx, game_name : str, subscriber_role : discord.Role,
                          max_slots : int, channel_above_id : int):
    channel_above = ctx.guild.get_channel(channel_above_id)
    if channel_above is None:
        raise commands.errors.BadArgument()

    db = read_database()
    if ctx.channel.id not in db.keys():
        await ctx.send(f"This channel has been activated for party matchmaking. " +
                       f"Use {BOT_CMD_PREFIX}startparty to create one!")
    else:
        await ctx.send(f"Channel configuration updated.")


    channel_info = ChannelInformation(ctx.channel, subscriber_role,
                                      max_slots, channel_above)
    db[ctx.channel.id] = channel_info
    save_database(db)


@activatechannel.error
async def activatechannel_error(ctx, error):
    error_handlers = get_default_error_handlers(ctx, "activatechannel",
                                                "GAME_NAME @SUBSCRIBER_ROLE " +
                                                "MAX_SLOTS CHANNEL_ABOVE_ID")
    await handle_error(ctx, error, error_handlers)


@bot.command()
@commands.has_role(BOT_ADMIN_ROLE)
async def deactivatechannel(ctx):
    check_channel(ctx.channel)
    db = read_database()
    del db[ctx.channel.id]
    save_database(db)
    await ctx.send(f"Party matchmaking disabled for this channel.")


@deactivatechannel.error
async def deactivatechannel_error(ctx, error):
    error_handlers = get_default_error_handlers(ctx, "deactivate", "")
    await handle_error(ctx, error, error_handlers)


@bot.event
async def on_raw_reaction_add(payload):
    await handle_react(payload, True)


@bot.event
async def on_raw_reaction_remove(payload):
    await handle_react(payload, False)


async def handle_react(payload, was_added):
    rp = await unwrap_payload(payload)
    if rp.member == rp.guild.me: # ignore bot reactions
        return
    if rp.message.author != rp.guild.me: # ignore reactions on non-bot messages
        return
    # ignore reactions on messages other than the party message
    # (identified by having exactly one embed)
    if len(rp.message.embeds) != 1:
        return

    if rp.emoji.name in emoji_handlers.keys():
        add_handler, remove_handler = emoji_handlers[rp.emoji.name]
        if was_added:
            await add_handler(rp)
        else:
            await remove_handler(rp)


async def add_member(rp):
    party = await Party.from_party_message(rp.message)
    if party.slots_left < 1 \
            or rp.member == party.leader: # leader can't join as member
        await rp.message.remove_reaction(Emojis.WHITE_CHECK_MARK, rp.member)
        return

    await party.add_member(rp.member, rp.message)
    if party.slots_left < 1:
        await handle_full_party(party, rp.message)


async def remove_member(rp):
    party = await Party.from_party_message(rp.message)
    if rp.member not in party.members:
        # This shouldn't happen. If it does, ignore it
        return
    if rp.member == party.leader: # leader can't leave
        return

    await party.remove_member(rp.member, rp.message)


async def handle_full_party(party, party_message):
    channel = party_message.channel
    guild = party_message.guild
    channel_info = read_database()[channel.id]
    channel_above = channel_info.get_channel_above(guild)
    category = guild.get_channel(channel_above.category_id)

    overwrites = {
        guild.default_role  : discord.PermissionOverwrite(read_messages=True,
                                                          connect=False),
        guild.me            : discord.PermissionOverwrite(read_messages=True),
        party.leader        : discord.PermissionOverwrite(read_messages=True,
                                                          connect=True)
    }
    overwrites.update({
        member              : discord.PermissionOverwrite(read_messages=True,
                                                          connect=True)
        for member in party.members
    })

    # TODO: game name in party channel name
    vc = await guild.create_voice_channel("party-%04i" % randint(0, 9999),
                                          category=category,
                                          overwrites=overwrites)
    await vc.edit(position=channel_above.position + 1)

    # edit original party message
    await party_message.edit(embed=None, content = \
        f"Matchmaking is done. If you're a member, " +
        f"you can now connect to {vc.mention}.")
    await party_message.clear_reactions()
    mentions = f"{party.leader.mention} " + \
               " ".join([m.mention for m in party.members])

    # send additional message, notifying members
    await channel.send(f"{mentions}. Matchmaking done. " +
                       f"Connect to {vc.mention}.")
    db = read_database()
    db[channel.id].unset_current_party_message()
    save_database(db)


# TODO: prevent instant deletion via timer
@bot.event
async def on_voice_state_update(member, before, after):
    channel = before.channel
    if channel is None\
            or not channel.name.startswith("party-"): # ignore other channels
        return
    if after.channel == channel: # only tracks disconnects
        return

    if len(channel.members) == 0:
        await channel.delete()


###############################################################################
## Utility functions and classes
###############################################################################
def read_database():
    '''Returns the database containing a (Channel ID) -> (ChannelInformation)
    mapping.'''
    if not os.path.exists(DATABASE_FILENAME):
        saveDatabase({}) # empty DB
    with open(DATABASE_FILENAME, "r") as f:
        raw_db = jsonpickle.loads(f.read())

    # json converts our int keys into string keys, have to undo that here
    db = {
        int(k): v
        for k, v in raw_db.items()
    }
    return db


def save_database(db):
    '''Saves the specified database.

    The database has to be a (Channel ID) -> (ChannelInformation) mapping.
    '''
    with open(DATABASE_FILENAME, "w") as f:
        f.write(jsonpickle.dumps(db))


class ChannelInformation():
    '''Contains the relevant information about an active channel.'''
    def __init__(self, game_name, channel, subscriber_role,
                 max_slots, channel_above):
        # Store all objects as their IDs to allow easier serialization
        self.game_name = game_name
        self.__channel_id = channel.id
        self.__subscriber_role_id = subscriber_role.id
        self.__current_party_message_id = None
        self.max_slots = max_slots
        self.__channel_above_id = channel_above.id

    async def get_current_party_message(self, guild):
        if self.__current_party_message_id == None:
            return None
        return await guild.get_channel(self.__channel_id)\
            .fetch_message(self.__current_party_message_id)

    def unset_current_party_message(self):
        self.__current_party_message_id = None

    def set_current_party_message(self, message):
        self.__current_party_message_id = message.id

    def get_subscriber_role(self, guild):
        return guild.get_role(self.__subscriber_role_id)

    def get_channel_above(self, guild):
        return guild.get_channel(self.__channel_above_id)


class Strings():
    PARTY_LEADER    = "Party leader"
    PARTY_MEMBERS   = "Party members"
    SLOTS_LEFT      = "Slots left"


async def get_active_party(channel):
    db = read_database()
    return await db[channel.id].get_current_party_message(channel.guild)


def check_channel(channel):
    '''Raises an InactiveChannelError if the channel is not marked as active.'''
    db = read_database()
    if channel.id not in db.keys():
        raise InactiveChannelError()


class InactiveChannelError(commands.CommandError): pass
class PartyAlreadyStartedError(commands.CommandError): pass
class NoActivePartyError(commands.CommandError): pass


def get_default_error_handlers(ctx, command_name, command_argument_syntax):
    '''Generate default error handlers including ones for bad argument syntax
    and invalid channel.
    '''
    usage_help = lambda: send_usage_help(ctx, command_name,
                                         command_argument_syntax)
    return {
        commands.errors.MissingRequiredArgument: usage_help,
        commands.errors.BadArgument: usage_help,
        commands.MissingRole: lambda:
        ctx.send("Insufficient rank permissions."),
        InactiveChannelError: lambda:
        ctx.send("The bot is not configured to use this channel. " +
                 f"Admins can change that via {BOT_CMD_PREFIX}activatechannel.")
    }


async def handle_error(ctx, error, error_handlers):
    for error_type, handler in error_handlers.items():
        if isinstance(error, error_type):
            await handler()
            return

    await send_error_unknown(ctx)
    raise error


def send_usage_help(ctx, function_name, argument_structure):
    return ctx.send("Usage: `%s%s %s`" \
                    % (BOT_CMD_PREFIX, function_name, argument_structure))


class ReactionPayload():
    # this might be a bit heavy on the API
    async def _init(self, payload):
        self.guild = bot.get_guild(payload.guild_id)
        self.member = await self.guild.fetch_member(payload.user_id)
        self.emoji = payload.emoji
        self.channel = bot.get_channel(payload.channel_id)
        self.message = await self.channel.fetch_message(payload.message_id)


async def unwrap_payload(payload):
    rp = ReactionPayload()
    await rp._init(payload)
    return rp


class Party():
    '''Python object representing an active party.

    This object is never saved to the database, as all the state is kept within
    Discord.
    Party objects can be reconstructed from party messages and can be used to
    create party messages.
    '''

    def __init__(self, channel, leader, slots_left, members=set()):
        self.channel = channel
        self.leader = leader
        self.slots_left = slots_left
        self.members = members

    async def from_party_message(message):
        embed = message.embeds[0]
        channel = message.channel
        guild = message.guild

        # fucking kill me please this is horrible coding
        members = set()
        for f in embed.fields:
            if f.name == Strings.PARTY_LEADER:
                leader = await guild.fetch_member(user_snowflake_to_id(f.value))
            if f.name == Strings.PARTY_MEMBERS:
                if f.value == "None":
                    continue
                members = f.value.split(" ")
                members = [await guild.fetch_member(user_snowflake_to_id(id))
                               for id in members]
                members = set(members)
            if f.name == Strings.SLOTS_LEFT:
                slots_left = int(f.value)

        return Party(channel, leader, slots_left, members)


    def to_embed(self):
        embed = discord.Embed.from_dict({
            "color": 0x00FF00,
            "description": f"{self.leader.mention} has just launched a party!\n" +
                        f"React with {BOT_JOIN_EMOJI} to join the party."
        })
        embed.add_field(name=Strings.PARTY_LEADER,
                        value=self.leader.mention, inline=True)
        embed.add_field(name=Strings.SLOTS_LEFT,
                        value=self.slots_left, inline=True)
        if len(self.members) > 0:
            members_value = " ".join([m.mention for m in self.members])
        else:
            members_value = "None"

        embed.add_field(name=Strings.PARTY_MEMBERS,
                        value=members_value, inline=True)

        return embed

    async def add_member(self, user, message):
        self.members.add(user)
        self.slots_left -= 1
        await message.edit(embed=self.to_embed())

    async def remove_member(self, user, message):
        self.members.remove(user)
        self.slots_left += 1
        await message.edit(embed=self.to_embed())


def user_snowflake_to_id(snowflake):
    if snowflake[2] == "!":
        return int(snowflake[3:-1])
    else:
        return int(snowflake[2:-1])


class Emojis():
    WHITE_CHECK_MARK = b'\xe2\x9c\x85'.decode()

# handle emoji reactions being added deleted/
# Format:
#   Emoji : (add_handler, remove_handler)
# All handlers are expected to take exactly one argument: the ReactionPayload
emoji_handlers = {
    Emojis.WHITE_CHECK_MARK: (add_member, remove_member),
}

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
