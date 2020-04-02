'''
This module includes various check functions that simplify common checks, such
as testing whether a user is a bot administrator.

The checks in this module come in two variants:
- Functions that return None when the check passes and raise an appropriate
  subclass of CommandError otherwise.
  These functions are prefixed with `check_`, such as `check_party_enabled`.
- Functions that return True when the check passes and False otherwise.
  These functions do *not* have the `check_` prefix.
'''

import discord
from database import db


def check_party_enabled(channel : discord.TextChannel) -> None:
    '''
    Raises an InactiveChannelError if the channel is not activated for the
    party feature.
    '''
    if channel.id not in db.party_channels:
        raise InactiveChannelError()


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
