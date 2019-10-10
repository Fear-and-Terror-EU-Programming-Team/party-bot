#######################################################################################
# Code info:
# Version = 1.0.0
#######################################################################################

# IMPORT
import discord

# SYSTEM VARIABLES (TOKEN TO BE CHANGED)
token = "NjMxNDkzMTE4NDk1MjkzNDQw.XZ3-TA.y0--IMOJRfKXoGGisQPwemPFnyQ"
client = discord.Client()

# SERVER VARIABLES (SERVER SPECIFIC)
allowed_channels = ["general"]  # list of allowed channels where the bot reads commands from
bot_commands = ["$StartRaid"]  # list with all the bot commands
raid_notification = "631524437879160874"  # role (id, str) the bot tags when announcing raid
raid_emoji = "✅"     # emoji to be reacted to join the raid
raid_channel_id = 631525965704724517   # channel (id, int) in which the bot announces a raid
bot_client = "FaT - Test Bot#4431"


# CODE
@client.event
async def on_message(message):
	###################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 09 / 2019
	# Purpose: To execute a line of code when a message gets sent in the discord server
	###################################################################################

	# VARIABLES
	raid_channel = client.get_channel(raid_channel_id)  # channel (id) in which the bot announces a raid
	raid_message = f"> <@&{raid_notification}> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raid_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5 so react fast!"

	# CODE
	if str(message.author) != bot_client:
		if str(message.channel) in allowed_channels:
			if message.content in bot_commands:
				if message.content.find(bot_commands[0]) != -1:
					await raid_channel.send(raid_message + "\n")
	else:
		await message.add_reaction(raid_emoji)


@client.event
async def on_reaction_add(reaction, user):
	channel = reaction.message.channel  # channel in which the emoji has been added
	message_author = reaction.message.author
	print(channel.id, type(channel.id))
	if channel.id == raid_channel_id:
		if message_author == bot_client:
			print(str(user), "reacted with", str(reaction), "in", channel)


client.run(token)
