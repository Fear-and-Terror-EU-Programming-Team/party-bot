'''
This module deals with the handling of emoji reactions in channels for which
one of the bot's features is enabled.

Most of the side games voice channel feature is implemented here.
'''

import channelinformation
import checks
import config
import discord
import party
import re
import scheduling
import sys
import transaction
import typing
from database import db
from discord.utils import get
from emojis import Emojis
from reaction_payload import ReactionPayload, unwrap_payload
from synchronization import synchronized

# handle emoji reactions being added / deleted
# Format:
#   Emoji : (add_handler, remove_handler)
# All handlers are expected to take exactly one argument: the ReactionPayload
party_emoji_handlers = {
    Emojis.WHITE_CHECK_MARK:
        (party.add_member_emoji_handler, party.remove_member_emoji_handler),
    Emojis.FAST_FORWARD:
        (party.force_start_party, None),
    Emojis.NO_ENTRY_SIGN:
        (party.close_party, None),
    Emojis.TADA:
        (party.start_party, None)
}

@synchronized
async def handle_react(payload : discord.RawReactionActionEvent,
                       added : bool) -> None:
    '''
    Executes the correct emoji handler for the specified `ReactionPayload`.

    If no appropriate emoji handler exists or the emoji handler returns
    `False`, then the emoji reaction is removed.

    For games channels, the generic games channels emoji handler is called.

    Note that this function is synchronized.
    Simultaneous calls to this function will be blocked and executed
    sequentially.
    '''

    rp = await unwrap_payload(payload)

    if rp.member == rp.guild.me:
        return # ignore bot reactions

    if checks.is_channel_inactive(rp.channel):
        return # ignore reactions in unrelated channels

    # Track whether the reaction should be kept or removed
    keep_reaction = False

    if checks.is_party_channel(rp.channel):
        if rp.message.author != rp.guild.me:
            return # ignore reactions on non-bot messages

        # ignore reactions on messages other than the party message
        # (identified by having exactly one embed)
        if len(rp.message.embeds) != 1:
            return

        if str(rp.emoji) not in party_emoji_handlers:
            await rp.message.remove_reaction(rp.emoji, rp.member)
            return

        # call appropriate handler
        add, remove = party_emoji_handlers[str(rp.emoji)]
        if added and add is not None:
            keep_reaction = await add(rp)
        elif not added and remove is not None:
            await remove(rp)

    if checks.is_side_games_channel(rp.channel) and added:
        await handle_react_side_games(rp)
        keep_reaction = False

    if checks.is_event_channel(rp.channel) and added:
        await handle_react_event_channel(rp)
        keep_reaction = False

    if not keep_reaction:
        try:
            await rp.message.remove_reaction(rp.emoji, rp.member)
        except discord.NotFound:
            pass # message was already deleted

    # save database
    transaction.commit()


async def handle_react_side_games(rp : ReactionPayload) -> None:
    '''
    Reaction handler for the side games voice channel feature.
    '''
    game_name = translate_emoji_game_name(rp.message, rp.emoji)
    if game_name is None:
        return # unknown emoji, ignore reaction

    channel_info = db.games_channels[rp.channel.id]

    # check if user already created a party channel
    vc_id = channel_info.channel_owners.get(rp.member.id)
    if vc_id is not None:
        # make sure it's actually still there
        if rp.guild.get_channel(vc_id) is None:
            print(f"VC deletion was not tracked!\n"
                  f"- Owner: {rp.member}\n", file=sys.stderr)
            del channel_info.channel_owners[rp.member.id]
        else:
            message = await rp.channel.send(f"{rp.member.mention} "
                                            f"You already have an open channel.")
            scheduling.message_delayed_delete(message)
            return

    if game_name not in channel_info.counters:
        channel_info.counters[game_name] = 0
    channel_info.counters[game_name] += 1
    counter = channel_info.counters[game_name]
    channel_below, channel_below_position = \
            await channel_info.fetch_channel_below(rp.guild)
    category = rp.guild.get_channel(channel_below.category_id)

    vc = await rp.guild.create_voice_channel(f"{game_name} - #{counter}",
                                             category=category)
    await vc.edit(position=channel_below_position + 0)
    channel_info.channel_owners.update({rp.member.id: vc.id})
    prot_delay_hours = config.GAMES_CHANNEL_GRACE_PERIOD_HOURS
    scheduling.channel_start_grace_period(vc, prot_delay_hours*3600,
                            delete_callback=side_games_deletion_callback,
                            delete_callback_args=[rp.channel.id])

    message = await rp.channel.send(f"{rp.member.mention} "
                                    f"Connect to {vc.mention}. "
                                    f"Your channel will stay open for "
                                    f"{prot_delay_hours} hours. "
                                    f"After that, it gets deleted as soon as "
                                    f"it empties out.")
    scheduling.message_delayed_delete(message)

    return # will always remove emoji reaction


async def handle_react_event_channel(rp: ReactionPayload) -> None:
    '''
    Reaction handler for the event voice channel feature.
    '''
    translation_tuple = translate_emoji_event_channels(rp.message, rp.emoji)
    if translation_tuple is None:
        return # unknown emoji, ignore reaction

    game_name, channel_name, position = translation_tuple

    try:
        channel_id = discord.utils.get(rp.guild.voice_channels, name=channel_name).id
    except discord.NotFound:
        message = await rp.channel.send(f"Channel {channel_name} not found.")
        scheduling.message_delayed_delete(message)
        return

    channel, channel_position = \
            await channelinformation.fetch_reference_channel(channel_id, rp.guild)
    category = rp.guild.get_channel(channel.category_id)

    counter = 1
    for channel in rp.guild.voice_channels:
        if channel.name.startswith(f"{game_name} - #"):
            counter += 1

    vc = await rp.guild.create_voice_channel(f"{game_name} - #{counter}",
                                             category=category)
    db.event_voice_channels.add(vc.id)

    if position: # if True the channel will be created above channel_position
        await vc.edit(position=channel_position + 0)
    else: # else (False) it will be created below channel_position
        await vc.edit(position=channel_position + 1)

    prot_delay_hours = config.EVENT_CHANNEL_GRACE_PERIOD_HOURS
    scheduling.channel_start_grace_period(vc, prot_delay_hours*3600)

    message = await rp.channel.send(f"{rp.member.mention} "
                                    f"Connect to {vc.mention}. "
                                    f"Your channel will stay open for "
                                    f"{prot_delay_hours} hours. "
                                    f"After that, it gets deleted as soon as "
                                    f"it empties out.")
    scheduling.message_delayed_delete(message)

    return # will always remove emoji reaction


def side_games_deletion_callback(voice_channel, games_channel_id):
    '''
    Callback for automatic deletion of side games channels.

    Users are only allowed to have a limited amount of side games voice channel
    at the same time.
    This callback ensures that auto-deleted channels no longer count towards
    this limit.
    '''
    channel_info = db.games_channels[games_channel_id]

    # get owner of channel and remove him from the channel_owners dict
    for owner_id, vc_id in channel_info.channel_owners.items():
        if vc_id == voice_channel.id:
            del channel_info.channel_owners[owner_id]
            break


async def add_first_emojis(message):
    '''
    Scans the message for menu entries (see `activate_side_games` command) and
    adds the appropriate emoji reactions to the message, allowing other members
    to click on the emoji icons.

    Note that messages made by non-admins and messages in channels for which
    the side games voice channel feature is not enabled are ignored.
    '''
    if not checks.is_admin(message.author):
        return # ignore non-admin message
    if checks.author_is_me(message):
        return # ignore bot messages

    if checks.is_event_channel(message.channel):
        translations = get_emoji_event_channels_translations(message)
        for emoji in translations.keys():
            await message.add_reaction(emoji)
        return # return if message in event channel

    if not checks.is_side_games_channel(message.channel):
        return # ignore messages in non-games channels

    translations = get_emoji_side_game_translations(message)
    for emoji in translations.keys():
        await message.add_reaction(emoji)


def get_emoji_side_game_translations(
    message: discord.Message) -> typing.Dict[str, str]:
    '''
    Scans the message for menu entries (see `activate_side_games` command)
    and returns a dict that contains all mapping from emojis to game names.
    Note that the dict contains the emojis in their string representation (as
    returned by `str(emoji)`).
    '''

    translations = {}
    pattern = r"> *([^ \n]+) +([^\n]+)"
    for match in re.finditer(pattern, message.content):
        expected_emoji, game_name = match.group(1,2)
        translations[expected_emoji] = game_name
    return translations


def get_emoji_event_channels_translations(
    message: discord.Message) -> typing.Dict[str, typing.Tuple[str, str, bool]]:
    '''
    Scans the message for event menu entries (see `activate_event_channel`
    command) and returns a dict that contains all mapping from emojis to game
    names, channel_names of the channel next to which the channel must be created.
    If it's above or below this channel is determined by position.
    Note that the dict contains the emojis in their string representation (as
    returned by `str(emoji)`).
    '''

    translations = {}
    pattern = r'> *([^ \n]+) +([^\n]+) \[(Above|Below) "([^\n]+)"\]'
    for match in re.finditer(pattern, message.content):
        expected_emoji, game_name, position, channel_name = match.group(1,2,3,4)
        pos = {"Above": True, "Below": False}
        position = pos[position]
        translations[expected_emoji] = (game_name, channel_name, position)
    return translations


def translate_emoji_game_name(message : discord.Message,
                              emoji : discord.Emoji) -> typing.Optional[str]:
    '''
    Scans the message for menu entries (see `activate_side_games` command),
    returning the game name associated with the emoji.
    If no matching menu entry is found, None is returned.
    '''
             
    emoji = str(emoji)

    # get all emoji-to-role translations by parsing the message
    translations = get_emoji_side_game_translations(message)
    return translations.get(emoji)


def translate_emoji_event_channels(message: discord.Message,
                              emoji: discord.Emoji) -> typing.Optional[typing.Tuple[str, str, bool]]:
    '''
    Scans the message for menu entries (see `activate_event_channel` command),
    returning the game name and the channel_name of the channel associated with the
    emoji next to which the channel must be created. If it's above or below this
    channel is determined by position.
    If no matching menu entry is found, None is returned.
    '''

    emoji = str(emoji)

    # get all emoji-to-role translations by parsing the message
    translations = get_emoji_event_channels_translations(message)
    return translations.get(emoji)
