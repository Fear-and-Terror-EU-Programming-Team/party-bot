########################################################################################################################
# Code info:
# Version = 1.0.0
########################################################################################################################

# IMPORT
import discord
from discord.utils import get
import json

# SYSTEM VARIABLES
database_directory = "database.json"  # directory of the .json file to be used for some short data storage
client = discord.Client()

# EMPTY VARIABLES
raid_leader = None
raid_message = None
raid_members = []
raid_active = False

raiders_leader = None
raiders_message = None
raiders_members = []
raiders_active = False

# FUNCTIONS


def read_database(category, dictionary=None, key=None):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 16 / 2019
	# Purpose: To read a key from a dictionary from a category in the .json file
	####################################################################################################################

	# VARIABLES
	global database_directory

	# READ
	current_file = open(database_directory, "r")
	json_text = json.load(current_file)
	current_file.close()

	# RETURN
	if category == "text":
		result = json_text
	else:
		result = json_text[category][dictionary][key]
	return result


def write_database(category, dictionary, key, new_value):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 16 / 2019
	# Purpose: To replace the value of a key from a dictionary from a category in the .json file
	####################################################################################################################

	# VARIABLES
	global database_directory

	# READ
	current = read_database(category, dictionary, key)
	json_text = read_database("text")

	# WRITE
	json_text[category][dictionary][key] = json_text[category][dictionary][key].replace(current, str(new_value))
	current_file = open(database_directory, "w")
	json.dump(json_text, current_file, indent=4)
	current_file.close()


# SERVER VARIABLES (SERVER SPECIFIC)
# bot
bot_commands = read_database("tarkov_bot", "bot", "bot_commands")  # list with all the bot commands (don't change the order!)
bot_token = read_database("tarkov_bot", "bot", "bot_token")
bot_client = read_database("tarkov_bot", "bot", "bot_client")

# general
allowed_channels = read_database("tarkov_bot", "general", "allowed_channels")  # list of allowed channels where the bot reads commands from
allowed_role = read_database("tarkov_bot", "general", "allowed_role")  # users with this role will be able to close by forcefully any raid

# role_assignment
role_assignment_emoji = read_database("tarkov_bot", "role_assignment", "role_assignment_emoji")     # emoji (emoji only, no id allowed) to be reacted to in order to receive the raid notification role
role_assignment_channel_id = read_database("tarkov_bot", "role_assignment", "role_assignment_channel_id")   # channel (id, int) in which the bot assigns the raid notification role
role_assignment_role = read_database("tarkov_bot", "role_assignment", "role_assignment_role")  # role to be assigned when reacting to the raid notification role assignment message

# raid
raid_role_id = read_database("tarkov_bot", "raid", "raid_role_id")  # role (id, str) the bot tags when announcing raid
raid_emoji = read_database("tarkov_bot", "raid", "raid_emoji")     # emoji (emoji only, no id allowed) to be reacted to join the raid
raid_channel_id = read_database("tarkov_bot", "raid", "raid_channel_id")   # channel (id, int) in which the bot announces a raid

# raiders
raiders_role = read_database("tarkov_bot", "raiders", "raiders_role")   # role (id, str) the bot tags when announcing a raiders-only raid
raiders_emoji = read_database("tarkov_bot", "raiders", "raiders_emoji")    # emoji (emoji only, no id allowed) to be reacted to join the raiders-only raid
raiders_channel_id = read_database("tarkov_bot", "raiders", "raiders_channel_id")   # channel (id, int) in which the bot announces a raiders-only raid
allowed_raiders = read_database("tarkov_bot", "raiders", "allowed_raiders")  # users with these roles (from lowest tear to highest) will be able to open a raiders-only raid

# CODE
@client.event
async def on_ready():
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 15 / 2019
	# Purpose: To execute a line of code when the bot becomes online
	####################################################################################################################
	# VARIABLES
	global role_assignment_channel_id
	raid_notification_channel = client.get_channel(role_assignment_channel_id)  # channel (id) in which the bot announces a raid
	notification_message_id = read_database("tarkov_bot", "role_assignment", "role_assignment_message_id")

	# CODE
	if notification_message_id != "None":
		await client.http.delete_message(raid_notification_channel.id, notification_message_id)
	await raid_notification_channel.send(f"If you want to be notified whenever a raid starts please react down "
										f"below with {role_assignment_emoji}.")


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

	global raiders_leader
	global raiders_message
	global raiders_active
	global raiders_members

	raid_channel = client.get_channel(raid_channel_id)  # channel (id) in which the bot announces a raid
	raiders_channel = client.get_channel(raiders_channel_id)  # channel (id) in which the bot announces a raiders-only raid
	server_members = client.get_all_members()   # all server members
	raid_text = f"> <@&{raid_role_id}> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raid_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5. So react fast!"
	raiders_text_1 = ""
	raiders_text_2 = f"\n> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raiders_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is 5. So react fast!"
	help_text = f"> Available general commands:" \
				f"\n> **{bot_commands[2]}**: List of server commands." \
				f"\n> \n> Available raids commands:" \
				f"\n> **{bot_commands[0]}**: Start a raid for other members to join." \
				f"\n> **{bot_commands[1]}**: Close __your own__ raid."  \
				f"\n> **{bot_commands[3]}**: Close forcibly someones raid. __You have to be a {allowed_role} to do so__." \
				f"\n> \n> Available raiders-raid commands:" \
				f"\n> **{bot_commands[4]}**: Start a raiders-only raid for other raiders to join. __You have to be a {allowed_raiders[0]}+ to do so__." \
				f"\n> **{bot_commands[5]}**: Close forcibly someones raiders-only raid. __You have to be a {allowed_role} to do so__." \
				f"\n> **{bot_commands[6]}**: Close __your own__ raiders-only raid"

	# CODE
	for role in raiders_role:
		raiders_text_1 += f"<@&{str(role)}> "
	raiders_text = "> " + raiders_text_1 + raiders_text_2

	if str(message.author) != bot_client:
		if str(message.channel) in allowed_channels:
			if message.content in bot_commands:

				# GENERAL COMMANDS
				# $Help
				if message.content.find(bot_commands[2]) != -1:
					await message.channel.send(help_text)

				# RAID COMMANDS
				# $StartRaid
				elif message.content.find(bot_commands[0]) != -1:
					if message.author != raiders_leader:
						if raid_active is False:
							raid_active = True
							raid_leader = message.author
							await raid_channel.send(raid_text)
						else:
							await message.channel.send("A raid is already active.")
					else:
						await message.channel.send("You already have an active raiders-only raid.")

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

				# $ForceCloseRaid
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

				# RAIDERS-ONLY RAID COMMANDS
				# $StartOnlyRaiders
				elif message.content.find(bot_commands[4]) != -1:
					has_role = False
					for author_role in message.author.roles:
						for role in allowed_raiders:
							if str(author_role) == role:
								has_role = True
					if has_role:
						if message.author != raid_leader:
							if raiders_active is False:
								raiders_active = True
								raiders_leader = message.author
								await raiders_channel.send(raiders_text)
							else:
								await message.channel.send("A raiders-only raid is already active.")
						else:
							await message.channel.send("You already have an active raid.")
					else:
						await message.channel.send(f"You have to be a {allowed_raiders[0]}+ to use this command.")

				# $CloseOnlyRaiders
				elif message.content.find(bot_commands[6]) != -1:
					if message.author == raiders_leader:
						await message.channel.send(
							f"<@{message.author.id}> your raid has been successfully closed.")
						await raiders_message.edit(content="> This raid has been closed by its leader.")
						raiders_leader = None
						raiders_active = False
						for user in raiders_members:
							await user.send("> The raid you joined has been closed by its leader.")
						for user in server_members:
							await raiders_message.remove_reaction(raid_emoji, user)
						raiders_members.clear()
					else:
						await message.channel.send("You don't have an active raid.")

				# $ForceCloseOnlyRaiders
				elif message.content.find(bot_commands[5]) != -1:
					if str(message.author.roles) in allowed_raiders:
						if raiders_leader is None:
							await message.channel.send("No active raiders-only raids.")
						else:
							await message.channel.send(f"<@{raiders_leader.id}> your raid was forcibly closed by "
														f"<@{message.author.id}>.")
							await raiders_message.edit(content=f"> This raid was forcibly closed by <@{message.author.id}>.")
							for user in raiders_members:
								await user.send(f"> The raid you joined was forcibly closed by <@{message.author.id}>.")
							for user in server_members:
								await raiders_message.remove_reaction(raid_emoji, user)
							raiders_leader = None
							raiders_active = False
							raiders_members.clear()
					else:
						await message.channel.send(f"You have to be a {allowed_role} to use this command.")

	else:
		if message.channel.id == raid_channel_id:
			raid_message = message
			await message.add_reaction(raid_emoji)
		elif message.channel.id == raiders_channel_id:
			raiders_message = message
			await message.add_reaction(raiders_emoji)
		elif message.channel.id == role_assignment_channel_id:
			await message.add_reaction(role_assignment_emoji)
			write_database("tarkov_bot", "role_assignment", "role_assignment_message_id", message.id)


@client.event
async def on_reaction_add(reaction, user):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 10 / 2019
	# Purpose: To execute a line of code when a reaction gets added to a message in the discord server
	####################################################################################################################

	# VARIABLES
	global raid_members
	global raiders_members
	min_members_num = 0
	max_num = 4 # max number of free member slots in the raid
	in_members = False
	# discord.utils.get(server.roles, name="Tarkov")

	# CODE
	for raider_member in raiders_members:
		for member in raid_members:
			if str(raider_member) == str(member):
				in_members = True

	# Raid data
	raid_num = max_num
	members_num = min_members_num
	for i in raid_members:
		raid_num -= 1
		members_num += 1

	if str(raid_members) == "[]":
		raid_text = "\n> People who have joined the raid"
	else:
		raid_text = ""

	# raiders-only raid data
	raiders_num = max_num
	raiders_members_num = min_members_num
	for i in raiders_members:
		raiders_num -= 1
		raiders_members_num += 1

	if str(raiders_members) == "[]":
		raiders_raid_text = "\n> People who have joined the raid"
	else:
		raiders_raid_text = ""

	# Raid message
	if reaction.message.channel.id == raid_channel_id:
		if str(reaction.message.author) == bot_client:
			if str(user) != bot_client and (user != raid_leader):
				if (user not in raid_members) and not in_members:
					if "Remember that the max amount of people to join is 5. So react fast!" in reaction.message.content:
						if raid_num != 0:
							raid_members.append(user)
							message_content = str(reaction.message.content)
							raid_num = max_num
							for member in raid_members:
								raid_num -= 1
							if raid_num == 1:
								slots_left_text = f"{str(raid_num)} slot left!"
								slots_left_text_ = f"{str(raid_num + 1)} slots left!"
							elif raid_num != 0:
								slots_left_text = f"{str(raid_num)} slots left!"
								slots_left_text_ = f"{str(raid_num + 1)} slots left!"
							else:
								slots_left_text = "Raid full"
								slots_left_text_ = f"{str(raid_num + 1)} slot left!"
							message_content = message_content.replace(f"({slots_left_text_})", f"({slots_left_text})")
							await raid_leader.send(f"{user} joined your raid!")
							if members_num == 0:
								await reaction.message.edit(content=f"{message_content}{raid_text} ({slots_left_text}):\n> - <@{user.id}>")
							else:
								await reaction.message.edit(content=f"{message_content}{raid_text}\n> - <@{user.id}>")

	# Notification role message
	elif reaction.message.channel.id == role_assignment_channel_id:
		if str(reaction.message.author) == bot_client:
			if (str(user) != bot_client) and (role_assignment_role not in str(user.roles)):
				await user.add_roles(user, role_assignment_role)

	# Raiders-only message
	elif reaction.message.channel.id == raiders_channel_id:
		if str(reaction.message.author) == bot_client:
			if (str(user) != bot_client) and (user != raiders_leader):
				if (str(user) not in raiders_members) and (str(user) not in raid_members):
					if "Remember that the max amount of people to join is 5. So react fast!" in reaction.message.content:
						if raiders_num != 0:
							raiders_members.append(user)
							message_content = str(reaction.message.content)
							raiders_num = max_num
							for i in raiders_members:
								raiders_num -= 1
							if raiders_num == 1:
								raiders_slots_left_text = f"{str(raiders_num)} slot left!"
								raiders_slots_left_text_ = f"{str(raiders_num + 1)} slots left!"
							elif raiders_num > 1:
								raiders_slots_left_text = f"{str(raiders_num)} slots left!"
								raiders_slots_left_text_ = f"{str(raiders_num + 1)} slots left!"
							elif raiders_num < 1:
								raiders_slots_left_text = "Raid full"
								raiders_slots_left_text_ = f"{str(raiders_num + 1)} slot left!"
							message_content = message_content.replace(f"({raiders_slots_left_text_})", f"({raiders_slots_left_text})")
							await raiders_leader.send(f"{user} joined your raid!")
							if raiders_members_num == 0:
								await reaction.message.edit(content=f"{message_content}{raiders_raid_text} ({raiders_slots_left_text}):\n> - <@{user.id}>")
							else:
								await reaction.message.edit(content=f"{message_content}{raiders_raid_text}\n> - <@{user.id}>")


client.run(bot_token)
