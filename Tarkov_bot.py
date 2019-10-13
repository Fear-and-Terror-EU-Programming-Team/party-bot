########################################################################################################################
# Code info:
# Version = 1.0.0
########################################################################################################################

# IMPORT
import discord

# SYSTEM VARIABLES (ONLY TOKEN TO BE CHANGED)
token = "NjMxNDkzMTE4NDk1MjkzNDQw.XaNeZw.NxFHRDvBL6ZULdczTdS9MVXw3xc"
bot_client = "FaT - Test Bot#4431"
client = discord.Client()
raid_leader = ""
raid_message = ""

# SERVER VARIABLES (SERVER SPECIFIC)
allowed_channels = ["general"]  # list of allowed channels where the bot reads commands from
bot_commands = ["$StartRaid", "$CloseRaid", "$Help"]  # list with all the bot commands (don't change the order!)
raid_notification = "631524437879160874"  # role (id, str) the bot tags when announcing raid
raid_emoji = "✅"     # emoji to be reacted to join the raid
raid_channel_id = 631525965704724517   # channel (id, int) in which the bot announces a raid

# CODE
@client.event
async def on_message(message):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 09 / 2019
	# Purpose: To execute a line of code when a message gets sent in the discord server
	####################################################################################################################

	# VARIABLES
	raid_channel = client.get_channel(raid_channel_id)  # channel (id) in which the bot announces a raid
	raid_text = f"> <@&{raid_notification}> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raid_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5. So react fast!"
	help_text = f"> Available Commands:" \
				f"\n> **{bot_commands[2]}**: List of server commands." \
				f"\n> **{bot_commands[0]}**: Start a raid for other members to join." \
				f"\n> **{bot_commands[1]}**: Close __your own__ raid."
	global raid_leader
	global raid_message

	# CODE
	if str(message.author) != bot_client:
		if str(message.channel) in allowed_channels:
			if message.content in bot_commands:
				if message.content.find(bot_commands[0]) != -1:
					raid_leader = message.author
					await raid_channel.send(raid_text + "\n")
				elif message.content.find(bot_commands[1]) != -1:
					if message.author == raid_leader:
						await message.channel.send(f"<@{message.author.id}> your raid has been closed.\n")
						await raid_message.edit(content="This raid has been closed by its leader.")
				elif message.content.find(bot_commands[2]) != -1:
					await message.channel.send(help_text)
	else:
		if " joined your raid!" not in message.content:
			if " your raid has been closed" not in message.content:
				if "> Available Commands:" not in message.content:
					raid_message = message
					await message.add_reaction(raid_emoji)


@client.event
async def on_reaction_add(reaction, user):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 10 / 2019
	# Purpose: To execute a line of code when a reaction gets added to a message in the discord server
	####################################################################################################################

	# VARIABLES
	channel = reaction.message.channel  # channel in which the emoji has been added
	message_author = reaction.message.author    # user who reacted to the message
	raid_text = f"> <@&{raid_notification}> <@{raid_leader.id}> has started a raid!\n" \
					f"> React to this message with {raid_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5. So react fast!\n" \
					f"> People who have joined the raid:"

	if channel.id == raid_channel_id:
		if str(message_author) == bot_client:
			if str(user) != bot_client:
				await raid_leader.send(f"{user} joined your raid!")
				await reaction.message.edit(content=(raid_text + f"\n> -<@{user.id}>"))


client.run(token)
