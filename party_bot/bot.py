#!/usr/bin/env python3
'''
Fear and Terror's bot for party matchmaking on Discord
'''
import party
import config
import discord
import database
import channelinformation
from party import Party
from discord.ext import commands
from emojis import Emojis

bot = commands.Bot(command_prefix=config.BOT_CMD_PREFIX)

###############################################################################
## Events
###############################################################################
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


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
        if was_added and add_handler != None:
            await add_handler(rp)
        elif remove_handler != None:
            await remove_handler(rp)


# handle emoji reactions being added deleted/
# Format:
#   Emoji : (add_handler, remove_handler)
# All handlers are expected to take exactly one argument: the ReactionPayload
emoji_handlers = {
    Emojis.WHITE_CHECK_MARK:
        (party.add_member_emoji_handler, party.remove_member_emoji_handler),
    Emojis.FAST_FORWARD:
        (party.force_start_party, None),
}


@bot.event
async def on_voice_state_update(member, before, after):
    channel = before.channel
    if channel is None \
        or after.channel == channel: # only tracks disconnects
        return
    if len(channel.members) > 0: # only react on empty channels
        return

    # only track channels created by the party bot
    db = database.load()
    mm_channel_id = None
    for cur_mm_channel_id, cur_mm_channel_info in db.items():
        if channel.id in cur_mm_channel_info.active_voice_channels:
            mm_channel_id = cur_mm_channel_id
            break
    if mm_channel_id == None:
        return

    await party.handle_party_emptied(mm_channel_id, channel)


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


###############################################################################
## Commands
###############################################################################

@bot.command()
async def startparty(ctx):
    check_channel(ctx.channel)
    if await channelinformation.get_active_party_message(ctx.channel) is not None:
        raise PartyAlreadyStartedError()

    db = database.load()
    subscriber_role = db[ctx.channel.id].get_subscriber_role(ctx.guild)
    max_slots = db[ctx.channel.id].max_slots
    party = Party(ctx.channel, ctx.author, max_slots - 1)
    message = await ctx.send(f"{subscriber_role.mention} {ctx.author.mention}",
                             embed=party.to_embed())
    db[ctx.channel.id].set_current_party_message(message)
    database.save(db)
    await message.add_reaction(Emojis.WHITE_CHECK_MARK)
    await message.add_reaction(Emojis.FAST_FORWARD)


@startparty.error
async def startparty_error(ctx, error):
    error_handlers = {
        PartyAlreadyStartedError: lambda:
        ctx.send("A party has already been launched in this channel. "
                 "Join that one or wait before creating another one.")
    }
    error_handlers.update(get_default_error_handlers(ctx, "startparty", ""))
    await handle_error(ctx, error, error_handlers)


@bot.command()
async def closeparty(ctx):
    check_channel(ctx.channel)
    party_message = await channelinformation.get_active_party_message(ctx.channel)
    if party_message is None:
        raise NoActivePartyError()
    admin_role = ctx.guild.get_role(config.BOT_ADMIN_ROLE)
    if party_message.author != ctx.author\
            and admin_role not in ctx.author.roles:
        raise commands.MissingRole()

    await ctx.send(f"> {ctx.author.mention} has just disbanded the party!\n"
                   f"> Type {config.BOT_CMD_PREFIX}startparty to launch a new party.")
    await party_message.delete()
    db = database.load()
    db[ctx.channel.id].unset_current_party_message()
    database.save(db)


@closeparty.error
async def closeparty_error(ctx, error):
    error_handlers = {
        NoActivePartyError: lambda:
        ctx.send("There is no active party in this channel.")
    }
    error_handlers.update(get_default_error_handlers(ctx, "closeparty", ""))
    await handle_error(ctx, error, error_handlers)


@bot.command()
@commands.has_role(config.BOT_ADMIN_ROLE)
async def activatechannel(ctx, game_name : str, subscriber_role : discord.Role,
                          max_slots : int, channel_above_id : int):
    channel_above = ctx.guild.get_channel(channel_above_id)
    if channel_above is None:
        raise commands.errors.BadArgument()

    db = database.load()
    if ctx.channel.id not in db.keys():
        await ctx.send(f"This channel has been activated for party matchmaking. "
                       f"Use {config.BOT_CMD_PREFIX}startparty to create one!")
    else:
        await ctx.send(f"Channel configuration updated.")


    channel_info = channelinformation.ChannelInformation(game_name, ctx.channel,
                                                         subscriber_role,
                                                         max_slots,
                                                         channel_above)
    db[ctx.channel.id] = channel_info
    database.save(db)


@activatechannel.error
async def activatechannel_error(ctx, error):
    error_handlers = get_default_error_handlers(ctx, "activatechannel",
                                                "GAME_NAME @SUBSCRIBER_ROLE "
                                                "MAX_SLOTS CHANNEL_ABOVE_ID")
    await handle_error(ctx, error, error_handlers)


@bot.command()
@commands.has_role(config.BOT_ADMIN_ROLE)
async def deactivatechannel(ctx):
    check_channel(ctx.channel)
    db = database.load()
    del db[ctx.channel.id]
    database.save(db)
    await ctx.send(f"Party matchmaking disabled for this channel.")


@deactivatechannel.error
async def deactivatechannel_error(ctx, error):
    error_handlers = get_default_error_handlers(ctx, "deactivate", "")
    await handle_error(ctx, error, error_handlers)


###############################################################################
## Command error handling
###############################################################################

class InactiveChannelError(commands.CommandError): pass
class PartyAlreadyStartedError(commands.CommandError): pass
class NoActivePartyError(commands.CommandError): pass


async def handle_error(ctx, error, error_handlers):
    for error_type, handler in error_handlers.items():
        if isinstance(error, error_type):
            await handler()
            return

    await send_error_unknown(ctx)
    raise error


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
        ctx.send(f"The bot is not configured to use this channel. "
                 f"Admins can change that via "
                 f"{config.BOT_CMD_PREFIX}activatechannel.")
    }

def send_usage_help(ctx, function_name, argument_structure):
    return ctx.send(f"Usage: `{config.BOT_CMD_PREFIX}{function_name} "
                    f"{argument_structure}`")


def send_error_unknown(ctx):
    return send_error(ctx, f"Unknown error. Tell someone from the programming"
                           f" team to check the logs.")


def send_error(ctx, text):
    return ctx.send("[ERROR] " + text)


def check_channel(channel):
    '''Raises an InactiveChannelError if the channel is not marked as active.'''
    db = database.load()
    if channel.id not in db.keys():
        raise InactiveChannelError()


###############################################################################
## Startup
###############################################################################

if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
