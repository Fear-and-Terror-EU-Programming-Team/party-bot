'''
This module includes various check functions that simplify common checks, such
as testing whether a user is a bot administrator.

The checks in this module come in two variants:
- Disord command predicate-style checks that return True when the check passes
  and raise an appropriate subclass of CommandError otherwise.
  These functions are prefixed with `check_`, such as `check_party_enabled`.
- Functions that return True when the check passes and False otherwise.
  These functions do *not* have the `check_` prefix.
'''

import discord
import error_handling
from database import db
from discord.ext import commands
from enum import enum



def author_is_me(message : discord.Message) -> bool:
    '''
    Returns true if and only if the author of the message is the bot user.
    '''
    return m.author == bot.user


def is_admin(member : discord.Member) -> bool:
    '''
    Returns true if and only if the user has any of the admin roles specified
    in config.BOT_ADMIN_ROLES.
    '''
    return any([role.id in config.BOT_ADMIN_ROLES for role in user.roles])


class ActivationState(enum):
    '''
    Enum of possible values returned by `get_active_feature`.
    '''

    # Channel is inactive
    INACTIVE = 0

    # Channel is activated for party matchmaking
    PARTY = 1

    # Channel is activated for side game channel creation
    SIDE_GAMES = 2


def get_active_feature(channel : discord.TextChannel) -> ActivationState:
    '''
    Returns an ActivationState describing which feature is currently activated
    in a `discord.TextChannel`.
    '''
    if channel.id in db.party_channels:
        return ActivationState.PARTY
    elif ctx.channel.id in db.games_channels:
        return ActivationState.SIDE_GAMES
    else:
        return ActivationState.INACTIVE


def is_channel_inactive(channel : discord.TextChannel) -> bool:
    '''
    Return True if and only if the channel is not activated for any feature.
    '''
    return get_active_feature(channel) == ActivationState.INACTIVE


def check_channel_inactive(ctx : commands.Context) -> bool:
    '''
    Raises a ChannelAlreadyActiveError if the channel is activated for any of
    the bot's features.
    '''
    if get_active_feature(ctx.channel) != ActivationState.INACTIVE:
        raise error_handling.ChannelAlreadyActiveError()
    else:
        return True


def is_party_channel(channel : discord.TextChannel) -> bool:
    '''
    Return True if and only if the channel is activated for party matchmaking.
    '''
    return get_active_feature(channel) == ActivationState.PARTY


def check_party_channel(ctx : commands.Context) -> bool:
    '''
    Raises an InactiveChannelError if the channel is not activated for the
    party feature.
    '''
    if get_active_feature(ctx.channel) != ActivationState.PARTY:
        raise error_handling.InactiveChannelError()
    else:
        return True


def is_side_games_channel(channel : discord.TextChannel) -> bool:
    '''
    Return True if and only if the channel is activated for the side game
    voice channel feature.
    '''
    return get_active_feature(channel) == ActivationState.SIDE_GAMES


def check_side_games_channel(ctx : commands.Context) -> bool:
    '''
    Raises an InactiveChannelError if the channel is not activated for the
    side games voice channel feature.
    '''
    if get_active_feature(ctx.channel) != ActivationState.SIDE_GAMES:
        raise error_handling.InactiveChannelError()
    else:
        return True
