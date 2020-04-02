#!/usr/bin/env -S python3 -u

'''
Fear and Terror's bot for party matchmaking on Discord
'''

import asyncio
import checks
import config
import discord
import emoji_handling
import error_handling
import party
import re
import scheduling
import sys
import transaction
import typing
from channelinformation import PartyChannelInformation, GamesChannelInformation
from database import db
from emojis import Emojis
from discord.ext import commands
from party import Party
from pprint import pprint
from strings import Strings
from synchronization import synchronized


bot = commands.Bot(command_prefix=config.BOT_CMD_PREFIX)

###############################################################################
## Events
###############################################################################
@bot.event
async def on_ready():
    config.init_config(bot)
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    scheduling.init_scheduler()


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    # Add first reactions to menu messages (see `activate_side_games`).
    # This is only relevant for the side games feature
    await emoji_handling.add_first_emojis(message)


@bot.event
async def on_raw_reaction_add(payload):
    await emoji_handling.handle_react(payload, True)


@bot.event
async def on_raw_reaction_remove(payload):
    await emoji_handling.handle_react(payload, False)


@bot.event
async def on_raw_message_edit(payload):
    '''
    Message edit handler that updates the bot's emoji reactions when a menu
    message (see `activate_side_games`) is edited.
    '''
    message = await bot.get_channel(payload.channel_id) \
        .fetch_message(payload.message_id)
    if payload.channel_id not in db.games_channels:
        return # ignore message outside of side games channels

    await message.clear_reactions()
    await emoji_handling.add_first_emojis(message)


@bot.event
async def on_command_error(ctx, error):
    await error_handling.handle_error(ctx, error)


@bot.event
async def on_voice_state_update(member, before, after):
    '''
    Event handler that takes cares of deleting bot-created channels when they
    empty out.
    '''
    channel = before.channel
    if channel is None \
            or after.channel == channel:  # only tracks disconnects
        return
    if len(channel.members) > 0:  # only react on empty channels
        return

    # ignore channels that are still in grace peroid
    if channel.id in scheduling.channel_ids_grace_period:
        return

    # only track channels created by the party bot
    # party channels
    for mm_id, info in db.party_channels.items():
        if channel.id in info.active_voice_channels:
            await party.handle_party_emptied(mm_id, channel)
            break

    # games channels
    for gc_id, info in db.games_channels.items():
        if channel.id in info.channel_owners.values():
            await channel.delete()
            # TODO: remove callback altogether?
            # Instead, we could simply update owner tracking information
            # whenever someone wants to create a new channel
            emoji_handling.side_games_deletion_callback(channel, gc_id)


###############################################################################
## Commands
###############################################################################

@bot.command(aliases = ["ap"])
@commands.has_any_role(config.BOT_ADMIN_ROLES)
async def activate_party(ctx, game_name: str,
                          max_slots: int, channel_above_id: int,
                          open_parties : str):
    '''
    Activates the party matchmaking feature for this channel, spawning a party
    creation menu.

    Attributes:
        game_name (str): The name of the game displayed in the party creation
            menu.
        max_slots (int): Maximum amount of players per party.
        channel_above_id (int): The ID of the voice channel below which the
            party voice channels will be created.
        open_parties (str): Either `OPEN_PARTIES` or `CLOSE_PARTIES`.
            Determines whether non-party members can join the voice chat.
            Note that anyone with the "Move Members" permission can always
            join party voice channels.

    To deactive the party matchmaking feature and remove the party creation
    menu, use the `deactivate_party` command.

    To edit the current configuration, simply run this command again.
    '''

    if not checks.is_channel_inactive(ctx.channel) \
            and not checks.is_party_channel(ctx.channel):
        raise error_handling.ChannelAlreadyActiveError()

    if open_parties == Strings.OPEN_PARTIES:
        open_parties = True
    elif open_parties == Strings.CLOSED_PARTIES:
        open_parties = False
    else:
        raise commands.errors.BadArgument()

    channel_above = ctx.guild.get_channel(channel_above_id)
    if channel_above is None:
        raise commands.errors.BadArgument()

    await ctx.message.delete()

    if checks.is_party_channel(ctx.channel):
        m = await ctx.send(f"Channel configuration updated.")
        scheduling.message_delayed_delete(m)
    else:
        m = await ctx.send(f"This channel has been activated for party "
                           f"matchmaking.")
        scheduling.message_delayed_delete(m)

    channel_info = PartyChannelInformation(game_name, ctx.channel, max_slots,
                                           channel_above, open_parties)

    db.party_channels[ctx.channel.id] = channel_info
    await ctx.channel.purge(limit=100, check=is_me)
    embed = discord.Embed.from_dict({
        "title": "Game: %s" % game_name,
        "color": 0x0000FF,
        "description": "React with %s to start a party for %s." \
                       % (Emojis.TADA, game_name)
    })
    message = await ctx.send("", embed=embed)
    await message.add_reaction(Emojis.TADA)


@bot.command(aliases = ["dp"])
@commands.has_any_role(config.BOT_ADMIN_ROLES)
@commands.check(checks.check_party_channel)
async def deactivate_party(ctx):
    '''
    Deactivates the party matchmaking feature for this channel, removing the
    party creation menu.
    '''
    del db.party_channels[ctx.channel.id]
    await ctx.message.delete()
    await ctx.channel.purge(limit=100, check=checks.is_me)
    message = await ctx.send(f"Party matchmaking disabled for this channel.")
    scheduling.message_delayed_delete(message)


# @bot.command()
# @commands.has_any_role(config.BOT_ADMIN_ROLES)
# async def nukeparties(ctx):
#    for channel in ctx.guild.channels:
#        if " Party #" in channel.name:
#            await channel.delete()


@bot.command(aliases = ["asg"])
@commands.has_any_role(config.BOT_ADMIN_ROLES)
@commands.check(checks.check_channel_inactive)
async def activate_side_games(ctx, channel_below_id: int):
    '''
    Activates the side game voice channel feature for this channel.
    Note that the voice channel creation menu has to be supplied seperately.
    See "Menu Formatting" below.

    Attributes:
        channel_below_id (int): The ID of the voice channel above which the
            voice channels will be created.

    Menu Formatting:
        The bot watches all menu messages in channels for which this feature
        is activated.
        Menu messages are messages that
        - Have been posted by a member that has any of the bot administrator
          roles specified in the bot configuration (config.BOT_ADMIN_ROLES).
        - Contain at least one menu entry (see below).

        Menu entries are lines in a menu message that have the following
        format:
        ```
        > EMOJI SIDE_GAME_NAME
        ```
        `EMOJI` must be either a Unicode emoji or a custom emoji.
        `SIDE_GAME_NAME` must be a sequence of any characters except a
        line-break.
        Note that the quote character (`>`) has to be the first character in
        the line.

        There can be multiple menu entries per menu and there can be multiple
        menus per channel.

        Example:
            ```
            > :map: Strategy Games
            > :Minecraft: Minecraft
            ```

    To deactive this feature, use the `deactivate_party` command.
    '''

    channel_below = ctx.guild.get_channel(channel_below_id)
    if channel_below is None:
        raise commands.errors.BadArgument()

    await ctx.message.delete()
    message = await ctx.send(f"Channel activated for side game voice "
                             f"channel creation.")
    scheduling.message_delayed_delete(message)

    channel_info = GamesChannelInformation(ctx.channel, channel_below)
    db.games_channels[ctx.channel.id] = channel_info


@bot.command(aliases = ["dsg"])
@commands.has_any_role(config.BOT_ADMIN_ROLES)
@commands.check(checks.check_side_games_channel)
async def deactivate_side_games(ctx):
    '''
    Deactivates the side game voice channel feature for this channel.
    '''

    await ctx.message.delete()
    message = await ctx.send(f"Side game voice channel creation disabled for "
                             f"this channel.")
    scheduling.message_delayed_delete(message)

    del db.games_channels[ctx.channel.id]


###############################################################################
## Startup
###############################################################################

if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
