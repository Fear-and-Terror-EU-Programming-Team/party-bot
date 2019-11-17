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
raid_removed_members = []
raid_active = False

raiders_leader = None
raiders_message = None
raiders_members = []
raiders_removed_members = []
raiders_active = False

# FUNCTIONS


def read_database(category, dictionary=None, key=None, index=None):
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
		if index is None:
			result = json_text[category][dictionary][key]
		else:
			result = json_text[category][dictionary][key][index]
	return result


def write_database(category, dictionary, key, new_value, index=None):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 16 / 2019
	# Purpose: To replace the value of a key from a dictionary from a category in the .json file
	####################################################################################################################

	# VARIABLES
	global database_directory

	# READ
	if index is None:
		current = read_database(category, dictionary, key)
	else:
		current = read_database(category, dictionary, key, index)
	json_text = read_database("text")

	# WRITE
	if index is None:
		json_text[category][dictionary][key] = str(json_text[category][dictionary][key]).replace(str(current), str(new_value))
	else:
		json_text[category][dictionary][key][index] = str(json_text[category][dictionary][key][index]).replace(str(current), str(new_value))
	current_file = open(database_directory, "w")
	json.dump(json_text, current_file, indent=4)
	current_file.close()


# SERVER VARIABLES (SERVER SPECIFIC) [info on each variable can be found in the .json file]
# bot
bot_commands = read_database("tarkov_bot", "bot", "bot_commands")
bot_token = read_database("tarkov_bot", "bot", "bot_token")
bot_client = read_database("tarkov_bot", "bot", "bot_client")

# general
allowed_channels = read_database("tarkov_bot", "general", "allowed_channels")
allowed_roles = read_database("tarkov_bot", "general", "allowed_roles")
bot_activity = read_database("tarkov_bot", "general", "bot_activity")

# role_assignment
role_assignment_emojis = read_database("tarkov_bot", "role_assignment", "role_assignment_emojis")
role_assignment_channel_ids = read_database("tarkov_bot", "role_assignment", "role_assignment_channel_ids")
role_assignment_roles = read_database("tarkov_bot", "role_assignment", "role_assignment_roles")

# raid
raid_role_id = read_database("tarkov_bot", "raid", "raid_role_id")
raid_emoji = read_database("tarkov_bot", "raid", "raid_emoji")
raid_channel_id = read_database("tarkov_bot", "raid", "raid_channel_id")
raid_allowed_channel = read_database("tarkov_bot", "raid", "raid_allowed_channel")

# raiders
raiders_role = read_database("tarkov_bot", "raiders", "raiders_role")
raiders_emoji = read_database("tarkov_bot", "raiders", "raiders_emoji")
raiders_channel_id = read_database("tarkov_bot", "raiders", "raiders_channel_id")
raiders_allowed_channel = read_database("tarkov_bot", "raiders", "raiders_allowed_channel")
allowed_raiders = read_database("tarkov_bot", "raiders", "allowed_raiders")

# SECONDARY VARIABLES
max_num = 4  # max number of free member slots in a raid


# CODE
@client.event
async def on_ready():
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 15 / 2019
	# Purpose: To execute a line of code when the bot becomes online
	####################################################################################################################
	# VARIABLES
	role_assignment_message_ids = read_database("tarkov_bot", "role_assignment", "role_assignment_message_ids")
	raid_notification_channel = client.get_channel(role_assignment_channel_ids[0])
	raiders_notification_channel = client.get_channel(role_assignment_channel_ids[1])

	# CODE
	if role_assignment_message_ids[0] is not None:
		await client.http.delete_message(raid_notification_channel.id, role_assignment_message_ids[0])
	if role_assignment_message_ids[1] is not None:
		await client.http.delete_message(raiders_notification_channel.id, role_assignment_message_ids[1])
	await raid_notification_channel.send(f"If you want to be notified whenever a raid starts please react down below with {role_assignment_emojis[0]}.")
	await raiders_notification_channel.send(f"If you want to be notified whenever a raid starts please react down below with {role_assignment_emojis[1]}.")
	if bot_activity is not None:
		await client.change_presence(status=discord.Status.online, activity=discord.Game(name=bot_activity), afk=False)


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
	global raid_removed_members

	global raiders_leader
	global raiders_message
	global raiders_active
	global raiders_members
	global raiders_removed_members

	raid_channel = client.get_channel(raid_channel_id)  # channel (id) in which the bot announces a raid
	raiders_channel = client.get_channel(
		raiders_channel_id)  # channel (id) in which the bot announces a raiders-only raid

	raid_text = f"> <@&{raid_role_id}> <@{message.author.id}> has started a raid!\n" \
				f"> React to this message with {raid_emoji} if you want to join it!\n" \
				f"> Remember that the max amount of people to join is {max_num}. So react fast!"
	raiders_text = f"\n> <@&{raiders_role}> <@{message.author.id}> has started a raid!\n" \
					f"> React to this message with {raiders_emoji} if you want to join it!\n" \
					f"> Remember that the max amount of people to join is {max_num}. So react fast!"
	help_text = f"> Available general commands:" \
				f"\n> **{bot_commands[2]}**: List of server commands." \
				f"\n> \n> Available raids commands:" \
				f"\n> **{bot_commands[0]}**: Start a raid for other members to join." \
				f"\n> **{bot_commands[1]}**: Close __your own__ raid." \
				f"\n> **{bot_commands[3]}**: Close forcibly someones raid. __You have to be a {allowed_roles[0]}+ to do so__." \
				f"\n> \n> Available raiders-raid commands:" \
				f"\n> **{bot_commands[4]}**: Start a raiders-only raid for other raiders to join. __You have to be a {allowed_raiders[0]}+ to do so__." \
				f"\n> **{bot_commands[6]}**: Close __your own__ raiders-only raid" \
				f"\n> **{bot_commands[5]}**: Close forcibly someones raiders-only raid. __You have to be a {allowed_roles[0]}+ to do so__."

	# CODE
	if str(message.author) != bot_client:
		if str(message.channel) in allowed_channels:
			if message.content in bot_commands:

				# GENERAL COMMANDS
				# $Help
				if message.content.find(bot_commands[2]) != -1:
					await message.channel.send(help_text)
					return

				# RAID COMMANDS
				# $StartRaid
				if message.content.find(bot_commands[0]) != -1:
					if str(message.channel) == raid_allowed_channel:
						if message.author != raiders_leader:
							if raid_active is False:
								raid_active = True
								raid_leader = message.author
								await raid_channel.send(raid_text)
							else:
								await message.channel.send("A raid is already active.")
						else:
							await message.channel.send("You already have an active raiders-only raid.")
					else:
						await message.channel.send("You can not use this command in this channel.")

				# $CloseRaid
				elif message.content.find(bot_commands[1]) != -1:
					if str(message.channel) == raid_allowed_channel:
						if message.author == raid_leader:
							await message.channel.send(
								f"<@{message.author.id}> your raid has been successfully closed.")
							await raid_message.edit(content="> This raid has been closed by its leader.")
							raid_leader = None
							raid_active = False
							for user in raid_members:
								await user.send("> The raid you joined has been closed by its leader.")
							await raid_message.clear_reactions()
							raid_members.clear()
							raid_removed_members.clear()
						else:
							await message.channel.send("You don't have an active raid.")
					else:
						await message.channel.send("You can not use this command in this channel.")

				# $ForceCloseRaid
				elif message.content.find(bot_commands[3]) != -1:
					if str(message.channel) == raid_allowed_channel:
						i = 0
						done = False
						while not done:
							for allowed in allowed_roles:
								if allowed in str(message.author.roles):
									done = True
									if raid_leader is None:
										await message.channel.send("No active raids.")
									else:
										await message.channel.send(
											f"<@{raid_leader.id}> your raid was forcibly closed by "
											f"<@{message.author.id}>.")
										await raid_message.edit(
											content=f"> This raid was forcibly closed by <@{message.author.id}>.")
										for user in raid_members:
											await user.send(
												f"> The raid you joined was forcibly closed by <@{message.author.id}>.")
										await raid_message.clear_reactions()
										raid_leader = None
										raid_active = False
										raid_members.clear()
										raid_removed_members.clear()
								elif i == len(allowed_roles):
									done = True
									await message.channel.send(
										f"You don't have high enough permissions to use this command.")
									break
								else:
									i += 1
					else:
						await message.channel.send("You can not use this command in this channel.")

				# RAIDERS-ONLY RAID COMMANDS
				# $StartOnlyRaiders
				elif message.content.find(bot_commands[4]) != -1:
					if str(message.channel) == raiders_allowed_channel:
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
					else:
						await message.channel.send("You can not use this command in this channel.")

				# $CloseOnlyRaiders
				elif message.content.find(bot_commands[6]) != -1:
					if str(message.channel) == raiders_allowed_channel:
						if message.author == raiders_leader:
							await message.channel.send(
								f"<@{message.author.id}> your raid has been successfully closed.")
							await raiders_message.edit(content="> This raid has been closed by its leader.")
							raiders_leader = None
							raiders_active = False
							for user in raiders_members:
								await user.send("> The raid you joined has been closed by its leader.")
							await raiders_message.clear_reactions()
							raiders_members.clear()
							raiders_removed_members.clear()
						else:
							await message.channel.send("You don't have an active raid.")
					else:
						await message.channel.send("You can not use this command in this channel.")

				# $ForceCloseOnlyRaiders
				elif message.content.find(bot_commands[5]) != -1:
					if str(message.channel) == raiders_allowed_channel:
						if str(message.author.roles) in allowed_raiders:
							i = 0
							done = False
							while not done:
								for allowed in allowed_roles:
									if allowed in str(message.author.roles):
										done = True
										if raiders_leader is None:
											await message.channel.send("No active raiders-only raids.")
										else:
											await message.channel.send(
												f"<@{raiders_leader.id}> your raid was forcibly closed by "
												f"<@{message.author.id}>.")
											await raiders_message.edit(
												content=f"> This raid was forcibly closed by <@{message.author.id}>.")
											for user in raiders_members:
												await user.send(
													f"> The raid you joined was forcibly closed by <@{message.author.id}>.")
											await raiders_message.clear_reactions()
											raiders_leader = None
											raiders_active = False
											raiders_members.clear()
											raiders_removed_members.clear()
									elif i == len(allowed_roles):
										done = True
										await message.channel.send(
											f"You don't have high enough permissions to use this command.")
										break
									else:
										i += 1
						else:
							await message.channel.send(f"You have to be a {allowed_roles[0]}+ to use this command.")
					else:
						await message.channel.send("You can not use this command in this channel.")

	else:
		if message.channel.id == raid_channel_id:
			raid_message = message
			await message.add_reaction(raid_emoji)
		elif message.channel.id == raiders_channel_id:
			raiders_message = message
			await message.add_reaction(raiders_emoji)
		elif message.channel.id == role_assignment_channel_ids[0]:
			await message.add_reaction(role_assignment_emojis[0])
			write_database("tarkov_bot", "role_assignment", "role_assignment_message_ids", message.id, 0)
		elif message.channel.id == role_assignment_channel_ids[1]:
			await message.add_reaction(role_assignment_emojis[1])
			write_database("tarkov_bot", "role_assignment", "role_assignment_message_ids", message.id, 1)


@client.event
async def on_reaction_add(reaction, user):
	####################################################################################################################
	# Author: ʝυʂƚ α ɳσɾɱαʅ ɠυყ
	# DateCreated: 10 / 10 / 2019
	# Purpose: To execute a line of code when a reaction gets added to a message in the discord server
	####################################################################################################################

	# VARIABLES
	global raid_leader
	global raid_members
	global raid_active

	global raiders_leader
	global raiders_members
	global raiders_active

	min_members_num = 0
	server_members = client.get_all_members()  # all server members
	in_members = False
	to_replace = f"> React to this message with {raiders_emoji}" \
				f" if you want to join it!\n" \
				f"> Remember that the max amount of people to join is {max_num}. So react fast!"
	to_replace_with = "> **This raid is now full.**"

	# CODE
	for raider_member in raiders_members:
		for member in raid_members:
			if str(raider_member) == str(member):
				in_members = True

	# Raid data
	raid_num = max_num
	members_num = min_members_num
	for _ in raid_members:
		raid_num -= 1
		members_num += 1

	if str(raid_members) == "[]":
		raid_text = "\n> People who have joined the raid"
	else:
		raid_text = ""

	# raiders-only raid data
	raiders_num = max_num
	raiders_members_num = min_members_num
	for _ in raiders_members:
		raiders_num -= 1
		raiders_members_num += 1

	if str(raiders_members) == "[]":
		raiders_raid_text = "\n> People who have joined the raid"
	else:
		raiders_raid_text = ""

	# Raid message
	if reaction.message.channel.id == raid_channel_id:
		if str(reaction.message.author) == bot_client:
			if f"{reaction}" == f"{raid_emoji}":
				if (str(user) != bot_client) and (user != raid_leader):
					if (user not in raid_members) and (not in_members) and user not in raid_removed_members:
						if f"Remember that the max amount of people to join is {max_num}. So react fast!" in reaction.message.content:
							if raid_num != 0:
								raid_members.append(user)
								message_content = str(reaction.message.content)
								raid_num = max_num
								for _ in raid_members:
									raid_num -= 1
								if raid_num == 1:
									slots_left_text = f"({str(raid_num)} slot left!)"
									slots_left_text_ = f"{str(raid_num + 1)} slots left!"
								elif raid_num != 0:
									slots_left_text = f"({str(raid_num)} slots left!)"
									slots_left_text_ = f"{str(raid_num + 1)} slots left!"
								else:
									slots_left_text = ""
									slots_left_text_ = f"{str(raid_num + 1)} slot left!"
								message_content = message_content.replace(f"({slots_left_text_})", f"{slots_left_text}")
								await raid_leader.send(f"{user} joined your raid!")
								if members_num == 0:
									await reaction.message.edit(
										content=f"{message_content}{raid_text} {slots_left_text}:\n> - <@{user.id}>")
								else:
									await reaction.message.edit(content=f"{message_content}{raid_text}\n> - <@{user.id}>")
							if raid_num == 0:
								message_content = str(reaction.message.content)
								message_content = message_content.replace(to_replace, to_replace_with)
								await reaction.message.edit(content=f"{message_content}")
								await raid_leader.send(f"> The raid you started is now full. Please contact all members.")
								for member in raid_members:
									await member.send(
										f"> The raid you joined is now full. Please contact the raid leader: <@{raid_leader.id}>.")
								for user in server_members:
									await raid_message.remove_reaction(raid_emoji, user)
								raid_leader = None
								raid_active = False
								raid_members.clear()

	# Raiders-only message
	elif reaction.message.channel.id == raiders_channel_id:
		if str(reaction.message.author) == bot_client:
			if f"{reaction}" == f"{raiders_emoji}":
				if (str(user) != bot_client) and (user != raiders_leader):
					if (str(user) not in raiders_members) and (not in_members):
						if f"Remember that the max amount of people to join is {max_num}. So react fast!" in reaction.message.content:
							if raiders_num != 0:
								raiders_members.append(user)
								message_content = str(reaction.message.content)
								raiders_num = max_num
								raiders_slots_left_text_ = None
								raiders_slots_left_text = None
								for _ in raiders_members:
									raiders_num -= 1
								if raiders_num == 1:
									raiders_slots_left_text = f"({str(raiders_num)} slot left!)"
									raiders_slots_left_text_ = f"{str(raiders_num + 1)} slots left!"
								elif raiders_num > 1:
									raiders_slots_left_text = f"({str(raiders_num)} slots left!)"
									raiders_slots_left_text_ = f"{str(raiders_num + 1)} slots left!"
								elif raiders_num < 1:
									raiders_slots_left_text = ""
									raiders_slots_left_text_ = f"{str(raiders_num + 1)} slot left!"
								message_content = message_content.replace(f"({raiders_slots_left_text_})", raiders_slots_left_text)
								await raiders_leader.send(f"{user} joined your raid!")
								if raiders_members_num == 0:
									await reaction.message.edit(
										content=f"{message_content}{raiders_raid_text} {raiders_slots_left_text}:\n> - <@{user.id}>")
								else:
									await reaction.message.edit(
										content=f"{message_content}{raiders_raid_text}\n> - <@{user.id}>")
							if raiders_num == 0:
								message_content = str(reaction.message.content)
								message_content = message_content.replace(to_replace, to_replace_with)
								await reaction.message.edit(content=f"{message_content}")
								await raiders_leader.send(
									f"> The raid you started is now full. Please contact all members.")
								for member in raiders_members:
									await member.send(
										f"> The raid you joined is now full. Please contact the raid leader: <@{raiders_leader.id}>.")
								for user in server_members:
									await raiders_message.remove_reaction(raiders_emoji, user)
								raiders_leader = None
								raiders_active = False
								raiders_members.clear()

	# Raid role assignment message
	elif reaction.message.channel.id == role_assignment_channel_ids[0]:
		if f"{reaction}" == f"{role_assignment_emojis[0]}":
			if str(reaction.message.author) == bot_client:
				if str(user) != bot_client:
					has_not_role = None
					for role in user.roles:
						if str(role) == role_assignment_roles[0]:
							has_not_role = False
					if not has_not_role:
						member_add_role = await reaction.message.guild.fetch_member(user.id)
						if not member_add_role:
							return
						role = get(reaction.message.guild.roles, name=role_assignment_roles[0])
						await member_add_role.add_roles(role)
						has_not_role = None
						for role in user.roles:
							if str(role) == role_assignment_roles[0]:
								has_not_role = False
						if has_not_role is not False:
							await user.send(f"You have successfully received the {role_assignment_roles[0]} role.")
						else:
							await user.send(f"There has been a problem with the assignment of the role. Please try again.\nIf the problem persists contact a staff member.")

	# Raiders role assignment message
	elif reaction.message.channel.id == role_assignment_channel_ids[1]:
		if f"{reaction}" == f"{role_assignment_emojis[1]}":
			if str(reaction.message.author) == bot_client:
				if str(user) != bot_client:
					has_not_role = None
					for role in user.roles:
						if str(role) == role_assignment_roles[1]:
							has_not_role = False
					if not has_not_role:
						member_add_role = await reaction.message.guild.fetch_member(user.id)
						if not member_add_role:
							return
						role = get(reaction.message.guild.roles, name=role_assignment_roles[1])
						await member_add_role.add_roles(role)
						has_not_role = None
						for role in user.roles:
							if str(role) == role_assignment_roles[1]:
								has_not_role = False
						if has_not_role is not False:
							await user.send(f"You have successfully received the {role_assignment_roles[1]} role.")
						else:
							await user.send(f"There has been a problem with the assignment of the role. Please try again.\nIf the problem persists contact a staff member.")


@client.event
async def on_reaction_remove(reaction, user):
	# VARIABLES
	global raid_removed_members

	global raiders_removed_members
	role_assignment_message_ids = read_database("tarkov_bot", "role_assignment", "role_assignment_message_ids")
	# CODE
	# Raid message
	if reaction.message.channel.id == raid_channel_id:
		if reaction.message.id == raid_message.id:
			if f"{reaction}" == f"{raid_emoji}":
				if user in raid_members and user not in raid_removed_members:
					if len(raid_members) != 0:
						raid_members.remove(user)
						raid_removed_members.append(user)
						await raid_leader.send(f"{user} left your raid.")

						# Edit message
						message_content = reaction.message.content
						members_num = len(raid_members)
						slots_num = max_num - members_num
						message_content = message_content.replace(f"> - <@{user.id}>", f"")
						if slots_num == max_num:
							message_content = message_content.replace(
								f"> People who have joined the raid ({slots_num - 1} slots left!):", f"")
						elif slots_num > 2:
							message_content = message_content.replace(f"({slots_num - 1} slots left!)",
																	f"({slots_num} slots left!)")
						elif slots_num == 2:
							message_content = message_content.replace(f"({slots_num - 1} slot left!)",
																	f"({slots_num} slots left!)")
						await reaction.message.edit(content=f"{message_content}")

	# Raiders-only message
	elif reaction.message.channel.id == raiders_channel_id:
		if reaction.message.id == raiders_message.id:
			if f"{reaction}" == f"{raiders_emoji}":
				if user in raiders_members and user not in raiders_removed_members:
					if len(raiders_members) != 0:
						raiders_members.remove(user)
						raiders_removed_members.append(user)
						await raiders_leader.send(f"{user} left your raid.")

						# Edit message
						message_content = reaction.message.content
						members_num = len(raiders_members)
						slots_num = max_num - members_num
						message_content = message_content.replace(f"> - <@{user.id}>", f"")
						if slots_num == max_num:
							message_content = message_content.replace(
								f"> People who have joined the raid ({slots_num - 1} slots left!):", f"")
						elif slots_num > 2:
							message_content = message_content.replace(f"({slots_num - 1} slots left!)",
																	f"({slots_num} slots left!)")
						elif slots_num == 2:
							message_content = message_content.replace(f"({slots_num - 1} slot left!)",
																	f"({slots_num} slots left!)")
						await reaction.message.edit(content=f"{message_content}")

	# Raid role assignment message
	elif str(reaction.message.id) == str(role_assignment_message_ids[0]):
		if f"{reaction}" == f"{role_assignment_emojis[0]}":
			has_role = None
			for role in user.roles:
				if str(role) == role_assignment_roles[0]:
					has_role = True
			if has_role:
				member_add_role = await reaction.message.guild.fetch_member(user.id)
				if not member_add_role:
					return
				role = get(reaction.message.guild.roles, name=role_assignment_roles[0])
				await member_add_role.remove_roles(role)
				has_role = None
				for role in user.roles:
					if str(role) == role_assignment_roles[0]:
						has_role = True
				if has_role is not True:
					await user.send(f"The removal of the {role_assignment_roles[0]} role was successful.")
				else:
					await user.send(f"There has been a problem with the removal of the role. Please try again.\nIf the problem persists contact a staff member.")

	# Raiders role assignment message
	elif str(reaction.message.id) == str(role_assignment_message_ids[1]):
		if f"{reaction}" == f"{role_assignment_emojis[1]}":
			has_role = None
			for role in user.roles:
				if str(role) == role_assignment_roles[1]:
					has_role = True
			if has_role:
				member_add_role = await reaction.message.guild.fetch_member(user.id)
				if not member_add_role:
					return
				role = get(reaction.message.guild.roles, name=role_assignment_roles[1])
				await member_add_role.remove_roles(role)
				has_role = None
				for role in user.roles:
					if str(role) == role_assignment_roles[1]:
						has_role = True
				if has_role is not True:
					await user.send(f"The removal of the {role_assignment_roles[1]} role was successful.")
				else:
					await user.send(f"There has been a problem with the removal of the role. Please try again.\nIf the problem persists contact a staff member.")

client.run(bot_token)
