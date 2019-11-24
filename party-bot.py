'''
Fear and Terror's bot for party matchmaking on Discord
'''
import discord
import os
from discord.utils import get
from discord.ext import commands
from config import *
import jsonpickle

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
    embed = discord.Embed.from_dict({
        "color": 0x00FF00,
        "description": f"{ctx.author.mention} has just launched a party!\n" +
                       f"React with {BOT_JOIN_EMOJI} to join the party."
    })
    embed.add_field(name=Strings.PARTY_LEADER,
                    value=ctx.author.mention, inline=True)
    embed.add_field(name=Strings.PARTY_MEMBERS,
                    value="None", inline=True)
    embed.add_field(name=Strings.SLOTS_LEFT,
                    value=db[ctx.channel.id].max_slots, inline=True)
    message = await ctx.send(f"{subscriber_role.mention} {ctx.author.mention}",
                             embed=embed)
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
async def activatechannel(ctx, subscriber_role : discord.Role, max_slots : int):
    db = read_database()
    if ctx.channel.id not in db.keys():
        await ctx.send(f"This channel has been activated for party matchmaking. " +
                       f"Use {BOT_CMD_PREFIX}startparty to create one!")
    else:
        await ctx.send(f"Channel configuration updated.")

    channel_info = ChannelInformation(ctx.channel, subscriber_role, max_slots)
    db[ctx.channel.id] = channel_info
    save_database(db)


@activatechannel.error
async def activatechannel_error(ctx, error):
    error_handlers = get_default_error_handlers(ctx, "activatechannel",
                                                "@SUBSCRIBER_ROLE MAX_SLOTS")
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
    rp = await unwrap_payload(payload)
    await rp.channel.send("react added")

    # TODO


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
    def __init__(self, channel, subscriber_role, max_slots):
        # Store all objects as their IDs to allow easier serialization
        self.__channel_id = channel.id
        self.__subscriber_role_id = subscriber_role.id
        self.__current_party_message_id = None
        self.max_slots = max_slots

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


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
