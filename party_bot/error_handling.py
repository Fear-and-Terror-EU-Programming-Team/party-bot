'''
This module defines
- various subclasses of CommandError that are used throughout
  this project
- a global error handler (`handle_error`) that is used to respond to various
  built-in and custom CommandErrors.
  This error handler should be called from `bot.on_command_error`.
'''

from discord.ext import commands


class ChannelAlreadyActiveError(commands.CommandError): pass


class ChannelDoubleActivateError(commands.CommandError): pass


class InactiveChannelError(commands.CommandError): pass


class PartyAlreadyStartedError(commands.CommandError): pass


class NoActivePartyError(commands.CommandError): pass


async def handle_error(ctx : commands.Context,
                       error : commands.CommandError) -> None:
    '''
    Global error handler.
    Responds to CommandErrors with appropriate messages in the Discord channel
    in which the command was used.

    This error handler should be called from `bot.on_command_error`.
    '''

    # Syntax errors
    syntax_error_classes = [
        commands.MissingRequiredArgument,
        commands.errors.BadArgument
    ]
    for cls in syntax_error_classes:
        if isinstance(error, cls):
            await ctx.send(f"{ctx.author.mention} Incorrect usage. "
                     f"See usage help below.")
            await ctx.send_help(ctx.command)
            return

    # Permission errors
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"{ctx.author.mention} You do not the role(s) required "
                       f"to use this command.")
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"{ctx.author.mention} Command is not applicable or "
                       f"lack the permission to use it.")
        return

    # State errors
    if isinstance(error, InactiveChannelError):
        await ctx.send(f"{ctx.author.mention} The requested feature is not"
                       f"activated for this channel.")
        return

    if isinstance(error, ChannelAlreadyActiveError):
        await ctx.send(f"{ctx.author.mention} The requested feature is"
                       f"already activated for this channel.")
        return

    if isinstance(error, ChannelDoubleActivateError):
        ctx.send(f"{ctx.author.mention} A channel can't be activated for "
                 f"multiple features!")
        return

    # Default catch-all
    ctx.send(f"{ctx.author.mention} An unknown error occurred. "
             f"Please contact the programming team and tell us what you did "
             f"to produce this error.")
