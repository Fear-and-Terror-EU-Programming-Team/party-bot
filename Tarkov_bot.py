########################################################################################################################
# Code info:
# Version = 1.0.0
########################################################################################################################

# IMPORT
import discord

# SERVER VARIABLES (SERVER SPECIFIC)
allowed_channels = ["general"]  # list of allowed channels where the bot reads commands from
allowed_role = "Moderator" # users with this role will be able to close by forcefully any raid
bot_commands = ["$StartRaid", "$CloseRaid", "$Help", "$ForceClose"]  # list with all the bot commands (don't change the order!)
raid_notification = "631524437879160874"  # role (id, str) the bot tags when announcing raid
raid_emoji = "✅"     # emoji to be reacted to join the raid
raid_channel_id = 631525965704724517   # channel (id, int) in which the bot announces a raid

# SYSTEM VARIABLES (ONLY TOKEN TO BE CHANGED)
token = "NjMxNDkzMTE4NDk1MjkzNDQw.XaOG9Q.WH6HmfY7ftNkpEfWMpx_gVERseo"
bot_client = "FaT - Test Bot#4431"
client = discord.Client()

# EMPTY VARIABLES
raid_leader = None
raid_message = None
raid_members = []
raid_active = False

# CODE
@client.event
async def on_message(message):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 09 / 2019
	# Purpose: To execute a line of code when a message gets sent in the discord server
	####################################################################################################################

	# VARIABLES
	global raid_leader
	global raid_message
	global raid_active
	global raid_members
	raid_channel = client.get_channel(raid_channel_id)  # channel (id) in which the bot announces a raid
	raid_text = f"> <@&{raid_notification}> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raid_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5. So react fast!"
	help_text = f"> Available Commands:" \
				f"\n> **{bot_commands[2]}**: List of server commands." \
				f"\n> **{bot_commands[0]}**: Start a raid for other members to join." \
				f"\n> **{bot_commands[1]}**: Close __your own__ raid."  \
				f"\n> **{bot_commands[3]}**: Close forcibly someone else's raid. __You have to be a {allowed_role} to do so__."

	# CODE
	if str(message.author) != bot_client:
		if str(message.channel) in allowed_channels:
			if message.content in bot_commands:

				# COMMANDS
				if message.content.find(bot_commands[0]) != -1:
					if raid_active is False:
						raid_active = True
						raid_leader = message.author
						await raid_channel.send(raid_text)
					else:
						await message.channel.send("A raid is already active.")

				elif message.content.find(bot_commands[1]) != -1:
					if message.author == raid_leader:
						await message.channel.send(f"<@{message.author.id}> your raid has been successfully closed.")
						await raid_message.edit(content="This raid has been closed by its leader.")
						raid_leader = None
						raid_active = False
						for user in raid_members:
							await user.send("The raid you joined has been closed by its leader.")
						raid_members.clear()
					else:
						await message.channel.send("You don't have an active raid.")

				elif message.content.find(bot_commands[2]) != -1:
					await message.channel.send(help_text)

				elif message.content.find(bot_commands[3]) != -1:
					if allowed_role in str(message.author.roles):
						if raid_leader is None:
							await message.channel.send("No active raids.")
						else:
							await message.channel.send(f"<@{raid_leader.id}> your raid was forcibly closed by "
														f"<@{message.author.id}>.")
							await raid_message.edit(content=f"This raid was forcibly closed by <@{message.author.id}>.")
							for user in raid_members:
								await raid_message.remove_reaction(raid_emoji)
							raid_leader = None
							raid_active = False
							raid_members.clear()
					else:
						await message.channel.send(f"You have to be a {allowed_role} to use this command.")
	else:
		if message.channel.id == raid_channel_id:
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
	global raid_members
	try:
		raid_text = f"> <@&{raid_notification}> <@{raid_leader.id}> has started a raid!\n" \
						f"> React to this message with {raid_emoji} if you want to join it!\n" \
						f"> Remember that the max amount of people to join is 5. So react fast!\n" \
						f"> People who have joined the raid:"
	except AttributeError:
		pass

	if reaction.message.channel.id == raid_channel_id:
		if str(reaction.message.author) == bot_client:
			if (str(user) != bot_client) and (str(user) not in raid_members):
				if "Remember that the max amount of people to join is 5. So react fast!" in reaction.message.content:
					raid_members.append(user)
					await raid_leader.send(f"{user} joined your raid!")
					await reaction.message.edit(content=(raid_text + f"\n> - <@{user.id}>"))


client.run(token)
