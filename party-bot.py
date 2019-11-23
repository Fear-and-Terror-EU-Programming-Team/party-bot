from discord.ext import commands
from config import *

bot = commands.Bot(command_prefix=bot_prefix)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def startparty(ctx):
    if ctx.channel.id in active_channels.keys() and active_channels[ctx.channel.id] is None:
        message = await ctx.send(f"> <@&{active_roles[ctx.channel.id]}> - {ctx.message.author.mention} has just "
                                 f"launched a party!\n "
                                 f"> React with {bot_emoji} to join the party.")
        await message.add_reaction(bot_emoji)
        active_channels[ctx.channel.id] = message.id
        active_leader[ctx.channel.id] = ctx.message.author.id
    else:
        await ctx.send("PARTY ALREADY STARTED REEEE")


@bot.command()
async def closeparty(ctx):
    if ctx.channel.id in active_channels.keys() and active_leader[ctx.channel.id] is not None:
        if ctx.message.author.id is active_leader[ctx.channel.id]:  # or user is bot_admin
            await ctx.send(f"> {ctx.message.author.mention} has just disbanded the party!\n"
                           f"> Type $StartParty to launch a new party.")
            # await bot.http.delete_message(ctx.channel.id, active_channels[ctx.channel.id])
            active_channels[ctx.channel.id] = None
            active_leader[ctx.channel.id] = None


@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.author is not bot.user.name:
        if reaction.message.id is active_channels[reaction.message.channel.id]:


async def launchparty(reaction, user):
    return

if __name__ == "__main__":
    bot.run(bot_token)
