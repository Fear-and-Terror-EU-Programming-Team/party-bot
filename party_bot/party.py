import asyncio
import config
import discord
from database import Database
from emojis import Emojis
from strings import Strings
from timers import channel_time_protection, channel_time_protection_set, \
                   message_delayed_delete


class Party():
    '''Python object representing an active party.

    This object is never saved to the database, as all the state is kept within
    Discord.
    Party objects can be reconstructed from party messages and can be used to
    create party messages.
    '''

    def __init__(self, channel, leader, slots_left, members=set()):
        self.channel = channel
        self.leader = leader
        self.slots_left = slots_left
        self.members = members

    async def from_party_message(message):
        embed = message.embeds[0]
        channel = message.channel
        guild = message.guild

        # fucking kill me please this is horrible coding
        members = set()
        for f in embed.fields:
            if f.name == Strings.PARTY_LEADER:
                leader = await guild.fetch_member(_user_snowflake_to_id(f.value))
            if f.name == Strings.PARTY_MEMBERS:
                if f.value == "None":
                    continue
                members = f.value.split(" ")
                members = [await guild.fetch_member(_user_snowflake_to_id(id))
                           for id in members]
                members = set(members)
            if f.name == Strings.SLOTS_LEFT:
                slots_left = int(f.value)

        return Party(channel, leader, slots_left, members)

    def to_embed(self):
        embed = discord.Embed.from_dict({
            "color": 0x00FF00,
            "description": f"{self.leader.mention} has just launched a party!\n"
                           f"React with {Emojis.WHITE_CHECK_MARK} to join the party. "
                           f"The party leader can start the party early with "
                           f"{Emojis.FAST_FORWARD} or close it with "
                           f"{Emojis.NO_ENTRY_SIGN}."
        })
        embed.add_field(name=Strings.PARTY_LEADER,
                        value=self.leader.mention, inline=True)
        embed.add_field(name=Strings.SLOTS_LEFT,
                        value=self.slots_left, inline=True)
        if len(self.members) > 0:
            members_value = " ".join([m.mention for m in self.members])
        else:
            members_value = "None"

        embed.add_field(name=Strings.PARTY_MEMBERS,
                        value=members_value, inline=True)

        return embed

    async def add_member(self, user, message):
        self.members.add(user)
        self.slots_left -= 1
        await message.edit(embed=self.to_embed())

    async def remove_member(self, user, message):
        self.members.remove(user)
        self.slots_left += 1
        await message.edit(embed=self.to_embed())


async def add_member_emoji_handler(rp):
    party = await Party.from_party_message(rp.message)
    message = rp.message
    channel = rp.channel
    db = Database.load()
    channel_info = db.party_channels()[str(channel.id)]

    if party.slots_left < 1 \
            or rp.member == party.leader:  # leader can't join as member
        await rp.message.remove_reaction(Emojis.WHITE_CHECK_MARK, rp.member)
        return
    if await channel_info.get_party_message_of_user(rp.member) is not None:
        delete_message = await channel.send(f"{rp.member.mention}, you are "
                                            f"already in another party! "
                                            f"Leave that party before trying "
                                            f"to join another.")
        asyncio.ensure_future(message_delayed_delete(delete_message))
        await rp.message.remove_reaction(Emojis.WHITE_CHECK_MARK, rp.member)
        return
    channel_info.set_party_message_of_user(rp.member, message)
    db.save()
    await party.add_member(rp.member, rp.message)
    if party.slots_left < 1:
        await handle_full_party(party, rp.message)


async def remove_member_emoji_handler(rp):
    party = await Party.from_party_message(rp.message)
    channel = rp.channel
    db = Database.load()
    channel_info = db.party_channels()[str(channel.id)]
    if rp.member not in party.members:
        # This shouldn't happen. If it does, ignore it
        return
    if rp.member == party.leader:  # leader can't leave
        return

    await party.remove_member(rp.member, rp.message)
    channel_info.clear_party_message_of_user(rp.member)
    db.save()


async def handle_full_party(party, party_message):
    channel = party_message.channel
    guild = party_message.guild
    db = Database.load()
    channel_info = db.party_channels()[str(channel.id)]
    channel_above, channel_above_position = \
            await channel_info.fetch_channel_above(guild)
    category = guild.get_channel(channel_above.category_id)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True,
                                                        connect=channel_info.open_parties),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        party.leader: discord.PermissionOverwrite(read_messages=True,
                                                  connect=True)
    }
    overwrites.update({
        member: discord.PermissionOverwrite(read_messages=True,
                                            connect=True)
        for member in party.members
    })

    # allow anyone with moving perms
    for role in guild.roles:
        if role.permissions.move_members:
            overwrites.update({
                role: discord.PermissionOverwrite(read_messages=True,
                                                  connect=True)
            })


    counter = channel_info.voice_channel_counter
    channel_info.voice_channel_counter += 1
    vc = await guild.create_voice_channel(f"{channel_info.game_name} "
                                          f"- Party - #{counter}",
                                          category=category,
                                          overwrites=overwrites)
    await vc.edit(position=channel_above_position + 1)
    channel_info.active_voice_channels.add(vc.id)

    # delete original party message
    mentions = f"{party.leader.mention} " + \
               " ".join([m.mention for m in party.members])
    trashcode = set()
    for m in party.members:
        db.party_channels()[str(channel.id)].clear_party_message_of_user(m)
    db.party_channels()[str(channel.id)].clear_party_message_of_user(party.leader)
    db.save()
    await party_message.delete()

    # send additional message, notifying members
    message = await channel.send(f"{mentions}. Matchmaking done. "
                                 f"Connect to {vc.mention}. "
                                 f"You have "
                                 f"{config.CHANNEL_TIME_PROTECTION_LENGTH_SECONDS} "
                                 f"seconds to join. "
                                 f"After that, the channel gets deleted as soon as it "
                                 f"empties out.")
    channel_time_protection_set.add(vc.id)
    asyncio.ensure_future(channel_time_protection(vc, callback=lambda vc:
                                                  channel_time_protection_set \
                                                  .remove(vc.id)))
    asyncio.ensure_future(message_delayed_delete(message))


async def force_start_party(rp):
    party = await Party.from_party_message(rp.message)
    # only leader can start the party
    # and don't start empty parties
    if rp.member != party.leader \
            or len(party.members) == 0:
        await rp.message.remove_reaction(Emojis.FAST_FORWARD, rp.member)
        return

    await handle_full_party(party, rp.message)


async def close_party(rp):
    party = await Party.from_party_message(rp.message)
    channel = party.channel
    if party.leader != rp.member \
            and not is_admin(rp.member):
        await rp.message.remove_reaction(Emojis.NO_ENTRY_SIGN, rp.member)
        return
    if rp.member != party.leader:
        message = await channel.send(f"> {rp.member.mention} has just force "
                                     f"closed {party.leader.mention}'s party!")
    else:
        message = await channel.send(f"> {rp.member.mention} has just "
                                     f"disbanded their party!\n")
    await rp.message.delete()
    db = Database.load()
    for m in party.members:
        db.party_channels()[str(channel.id)].clear_party_message_of_user(m)
    db.party_channels()[str(channel.id)].clear_party_message_of_user(party.leader)
    db.save()
    asyncio.ensure_future(message_delayed_delete(message))


async def start_party(rp):
    await rp.message.remove_reaction(Emojis.TADA, rp.member)
    channel = rp.channel
    db = Database.load()
    if str(channel.id) not in db.party_channels():
        # this happens if the channel got deactivated but
        # the menu wasn't deleted
        delete_message = await channel.send(f"Channel has not been configured "
                                            f"for party matchmaking")
        asyncio.ensure_future(message_delayed_delete(delete_message))
        return
    channel_info = db.party_channels()[str(channel.id)]

    if await channel_info.get_party_message_of_user(rp.member) is not None:
        delete_message = await channel.send(f"{rp.member.mention}, you are "
                                            f"already in another party! "
                                            f"Leave that party before trying "
                                            f"to create another one.")
        asyncio.ensure_future(message_delayed_delete(delete_message))
        return

    max_slots = channel_info.max_slots
    party = Party(channel, rp.member, max_slots - 1)
    message = await channel.send(embed=party.to_embed())
    await message.add_reaction(Emojis.WHITE_CHECK_MARK)
    await message.add_reaction(Emojis.FAST_FORWARD)
    await message.add_reaction(Emojis.NO_ENTRY_SIGN)
    channel_info.set_party_message_of_user(rp.member, message)
    db.save()


async def handle_party_emptied(matchmaking_channel_id, voice_channel):
    # grace period for new channels
    if voice_channel.id in channel_time_protection_set:
        return

    await voice_channel.delete()
    db = Database.load()
    db.party_channels()[str(matchmaking_channel_id)] \
        .active_voice_channels.remove(voice_channel.id)
    db.save()


def _user_snowflake_to_id(snowflake):
    if snowflake[2] == "!":
        return int(snowflake[3:-1])
    else:
        return int(snowflake[2:-1])


def is_admin(user):
    return any([role.id in config.BOT_ADMIN_ROLES for role in user.roles])


