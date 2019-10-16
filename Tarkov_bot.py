########################################################################################################################
# Code info:
# Version = 1.0.0
########################################################################################################################

# IMPORT
import discord
from discord.utils import get
import json

# SERVER VARIABLES (SERVER SPECIFIC)
bot_commands = ["$StartRaid", "$CloseRaid", "$Help", "$ForceClose"]  # list with all the bot commands (don't change the order!)

allowed_channels = ["general"]  # list of allowed channels where the bot reads commands from
allowed_role = "Moderator"  # users with this role will be able to close by forcefully any raid

raid_notification = "631524437879160874"  # role (id, str) the bot tags when announcing raid
raid_notification_emoji = "✅"     # emoji (emoji only, no id allowed) to be reacted to in order to receive the raid notification role
raid_notification_channel_id = 633736020738703400   # channel (id, int) in which the bot assigns the raid notification role
raid_notification_role = "Tarkov"  # role to be assigned when reacting to the raid notification role assignment message

raid_emoji = "✅"     # emoji (emoji only, no id allowed) to be reacted to join the raid
raid_channel_id = 631525965704724517   # channel (id, int) in which the bot announces a raid

database_directory = "database.json"  # directory of the .json file to be used for some short data storage

# SYSTEM VARIABLES (ONLY TOKEN TO BE CHANGED)
token = "NjMxNDkzMTE4NDk1MjkzNDQw.XaOG9Q.WH6HmfY7ftNkpEfWMpx_gVERseo"
bot_client = "FaT - Test Bot#4431"
client = discord.Client()

# EMPTY VARIABLES
raid_leader = None
raid_message = None
raid_members = []
raid_active = False

# FUNCTIONS


def read_database(dictionary, key=None):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 16 / 2019
	# Purpose: To read a key from a dictionary in the .json file
	####################################################################################################################

	# VARIABLES
	global database_directory

	# READ
	current_file = open(database_directory, "r")
	json_text = json.load(current_file)
	current_file.close()

	# RETURN
	if dictionary == "text":
		result = json_text
	else:
		result = json_text[dictionary][key]
	return result


def write_database(dictionary, key, new_value):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 16 / 2019
	# Purpose: To replace the value of a key from a dictionary in the .json file
	####################################################################################################################

	# VARIABLES
	global database_directory

	# READ
	current = read_database(dictionary, key)
	json_text = read_database("text")

	# WRITE
	json_text[dictionary][key] = json_text[dictionary][key].replace(current, str(new_value))
	current_file = open(database_directory, "w")
	json.dump(json_text, current_file, indent=2)
	current_file.close()

# CODE
@client.event
async def on_ready():
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 15 / 2019
	# Purpose: To execute a line of code when the bot becomes online
	####################################################################################################################
	# VARIABLES
	global raid_notification_channel_id
	raid_notification_channel = client.get_channel(raid_notification_channel_id)  # channel (id) in which the bot announces a raid
	notification_message_id = read_database("tarkov_bot", "notification_message_id")

	# CODE
	if notification_message_id != "None":
		await client.http.delete_message(raid_notification_channel.id, notification_message_id)
	await raid_notification_channel.send(f"If you want to be notified whenever a raid starts please react down "
										f"below with {raid_notification_emoji}.")


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
	server_members = client.get_all_members()   # all server members
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
				# $StartRaid
				if message.content.find(bot_commands[0]) != -1:
					if raid_active is False:
						raid_active = True
						raid_leader = message.author
						await raid_channel.send(raid_text)
					else:
						await message.channel.send("A raid is already active.")

				# $CloseRaid
				elif message.content.find(bot_commands[1]) != -1:
					if message.author == raid_leader:
						await message.channel.send(f"<@{message.author.id}> your raid has been successfully closed.")
						await raid_message.edit(content="> This raid has been closed by its leader.")
						raid_leader = None
						raid_active = False
						for user in raid_members:
							await user.send("> The raid you joined has been closed by its leader.")
						for user in server_members:
							await raid_message.remove_reaction(raid_emoji, user)
						raid_members.clear()
					else:
						await message.channel.send("You don't have an active raid.")

				# $Help
				elif message.content.find(bot_commands[2]) != -1:
					await message.channel.send(help_text)

				# $ForceClose
				elif message.content.find(bot_commands[3]) != -1:
					if allowed_role in str(message.author.roles):
						if raid_leader is None:
							await message.channel.send("No active raids.")
						else:
							await message.channel.send(f"<@{raid_leader.id}> your raid was forcibly closed by "
														f"<@{message.author.id}>.")
							await raid_message.edit(content=f"> This raid was forcibly closed by <@{message.author.id}>.")
							for user in raid_members:
								await user.send(f"> The raid you joined was forcibly closed by <@{message.author.id}>.")
							for user in server_members:
								await raid_message.remove_reaction(raid_emoji, user)
							raid_leader = None
							raid_active = False
							raid_members.clear()
					else:
						await message.channel.send(f"You have to be a {allowed_role} to use this command.")
	else:
		if message.channel.id == raid_channel_id:
			raid_message = message
			await message.add_reaction(raid_emoji)
		elif message.channel.id == raid_notification_channel_id:
			await message.add_reaction(raid_notification_emoji)
			write_database("tarkov_bot", "notification_message_id", message.id)


@client.event
async def on_reaction_add(reaction, user):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 10 / 2019
	# Purpose: To execute a line of code when a reaction gets added to a message in the discord server
	####################################################################################################################

	# VARIABLES
	global raid_members
	# discord.utils.get(server.roles, name="Tarkov")
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
					if user not in raid_members:
						raid_members.append(user)
						await raid_leader.send(f"{user} joined your raid!")
						await reaction.message.edit(content=(reaction.message.content + f"\n> - <@{user.id}>"))
	elif reaction.message.channel.id == raid_notification_channel_id:
		if str(reaction.message.author) == bot_client:
			if (str(user) != bot_client) and (raid_notification_role not in str(user.roles)):
				await user.add_roles(user, raid_notification_role)


client.run(token)
