"""
This module implements most of the party matchmaking feature.
"""

# necessary for typing factory methods
from __future__ import annotations

import asyncio
import checks
import config
import discord
import scheduling
from database import db
from emojis import Emojis
from reaction_payload import ReactionPayload
from strings import Strings


class Party:
    """Python object representing an active party.

    This object is never saved to the database, as all the state is kept within
    Discord.
    Party objects can be reconstructed from party messages and can be used to
    create party messages.
    """

    def __init__(self, channel, leader, slots_left, members=set()):
        self.channel = channel
        self.leader = leader
        self.slots_left = slots_left
        self.members = members

    async def from_party_message(message: discord.Message) -> Party:
        """
        Creates a Party object from a party message, parsing all embed fields
        to gather the necessary information.
        """

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
                members = [
                    await guild.fetch_member(_user_snowflake_to_id(id))
                    for id in members
                ]
                members = set(members)
            if f.name == Strings.SLOTS_LEFT:
                slots_left = int(f.value)

        return Party(channel, leader, slots_left, members)

    def to_embed(self) -> discord.Embed:
        """
        Creates a Discord embed used to represent the party.
        Messages containing this embed are called "party messages" and can be
        used to reconstruct this party object using `from_party_message`.
        """

        embed = discord.Embed.from_dict(
            {
                "color": 0x00FF00,
                "description": f"{self.leader.mention} has just launched a party!\n"
                f"React with {Emojis.WHITE_CHECK_MARK} to join the party. "
                f"The party leader can start the party early with "
                f"{Emojis.FAST_FORWARD} or close it with "
                f"{Emojis.NO_ENTRY_SIGN}.",
            }
        )
        embed.add_field(
            name=Strings.PARTY_LEADER, value=self.leader.mention, inline=True
        )
        embed.add_field(name=Strings.SLOTS_LEFT, value=self.slots_left, inline=True)
        if len(self.members) > 0:
            members_value = " ".join([m.mention for m in self.members])
        else:
            members_value = "None"

        embed.add_field(name=Strings.PARTY_MEMBERS, value=members_value, inline=True)

        return embed

    async def add_member(
        self, user: discord.Member, party_message: discord.Message
    ) -> None:
        """
        Adds a member to this party, updating this object and the party
        message.


        Note that this function does not check whether the party is full or
        whether the member is already part of the party.
        It also does not trigger party creation when the amount of free slots
        reach zero.
        """
        self.members.add(user)
        self.slots_left -= 1
        await party_message.edit(embed=self.to_embed())

    async def remove_member(
        self, user: discord.Member, party_message: discord.Message
    ) -> None:
        """
        Removes a member from this party, updating this object and the party
        message.

        Note that this function does not check whether whether the member is
        part of the party.
        If a non-party-member is removed from the party using this function,
        then `slots_left` will have an invalid value.
        """
        self.members.remove(user)
        self.slots_left += 1
        await party_message.edit(embed=self.to_embed())


async def add_member_emoji_handler(rp: ReactionPayload) -> bool:
    """
    Emoji handler that implements the party join feature.

    Will add a member to the party and trigger voice channel creation when the
    party is full.

    If the member that reacted is the party leader, the emoji is simply removed
    and no further action is taken.

    If the member is already part of another party, either as member or leader,
    an error message is printed and the emoji is removed.
    """

    party = await Party.from_party_message(rp.message)
    message = rp.message
    channel = rp.channel
    channel_info = db.party_channels[channel.id]

    if party.slots_left < 1 or rp.member == party.leader:  # leader can't join as member
        return False  # remove reaction
    if await channel_info.get_party_message_of_user(rp.member) is not None:
        delete_message = await channel.send(
            f"{rp.member.mention}, you are "
            f"already in another party! "
            f"Leave that party before trying "
            f"to join another."
        )
        scheduling.message_delayed_delete(delete_message)
        return False  # remove reaction
    channel_info.set_party_message_of_user(rp.member, message)
    await party.add_member(rp.member, rp.message)
    if party.slots_left < 1:
        await handle_full_party(party, rp.message)
    return True  # keep reaction


async def remove_member_emoji_handler(rp: ReactionPayload) -> None:
    """
    Emoji handler that implements the party leave feature.

    Will remove a member from the party.

    Since emoji reactions are handled sequentially but not in FIFO order, there
    is a small chance that the leave event is handled before the join event.
    In that case, the leave event is silently ignored.
    Note that this will cause the member to be part of the party.
    Since that member probably can't un-react without reacting first, the party
    has to be closed and re-opened to fix it.

    TODO: ensure FIFO order for the synchronization lock
    """

    party = await Party.from_party_message(rp.message)
    channel = rp.channel
    channel_info = db.party_channels[channel.id]

    # This shouldn't happen. If it does, ignore it
    # See function documentation above
    if rp.member not in party.members or rp.member == party.leader:
        return

    await party.remove_member(rp.member, rp.message)
    channel_info.clear_party_message_of_user(rp.member)


async def handle_full_party(party: Party, party_message: discord.Message) -> None:
    """
    Called by `Party.add_member` when a party reaches zero open slots.
    Deletes the party message and creates a party voice channel.
    Will inform all party members by posting a message in the party matchmaking
    channel.
    """
    channel = party_message.channel
    guild = party_message.guild
    channel_info = db.party_channels[channel.id]
    channel_above, channel_above_position = await channel_info.fetch_channel_above(
        guild
    )
    category = guild.get_channel(channel_above.category_id)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            read_messages=True, connect=channel_info.open_parties
        ),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        party.leader: discord.PermissionOverwrite(read_messages=True, connect=True),
    }
    overwrites.update(
        {
            member: discord.PermissionOverwrite(read_messages=True, connect=True)
            for member in party.members
        }
    )

    # allow anyone with moving perms
    for role in guild.roles:
        if role.permissions.move_members:
            overwrites.update(
                {role: discord.PermissionOverwrite(read_messages=True, connect=True)}
            )

    counter = channel_info.voice_channel_counter
    channel_info.voice_channel_counter += 1
    vc = await guild.create_voice_channel(
        f"{channel_info.game_name} " f"- Party - #{counter}",
        category=category,
        overwrites=overwrites,
    )
    await vc.edit(position=channel_above_position + 1)
    channel_info.active_voice_channels.add(vc.id)

    # delete original party message
    mentions = f"{party.leader.mention} " + " ".join([m.mention for m in party.members])
    for m in party.members:
        db.party_channels[channel.id].clear_party_message_of_user(m)
    db.party_channels[channel.id].clear_party_message_of_user(party.leader)
    await party_message.delete()

    # send additional message, notifying members
    message = await channel.send(
        f"{mentions}. Matchmaking done. "
        f"Connect to {vc.mention}. "
        f"You have "
        f"{config.PARTY_CHANNEL_GRACE_PERIOD_SECONDS} "
        f"seconds to join. "
        f"After that, the channel gets deleted as soon as it "
        f"empties out."
    )
    scheduling.channel_start_grace_period(vc, config.PARTY_CHANNEL_GRACE_PERIOD_SECONDS)
    scheduling.message_delayed_delete(message)


async def force_start_party(rp: ReactionPayload) -> None:
    """
    Emoji handler that implements the party force start feature.

    If the reacting member is not the party leader or the party has no members
    (excluding the party leader), the emoji is removed and no further action is
    taken.
    """

    party = await Party.from_party_message(rp.message)
    # only leader can start the party
    # and don't start empty parties
    if rp.member != party.leader or len(party.members) == 0:
        await rp.message.remove_reaction(Emojis.FAST_FORWARD, rp.member)
        return

    await handle_full_party(party, rp.message)


async def close_party(rp: ReactionPayload) -> None:
    """
    Emoji handler that implements the party close feature.

    If the reacting member is not the party leader or a bot admin as specified
    in `config.BOT_ADMIN_ROLES`, the emoji is removed and no further action is
    taken.

    Otherwise, the party message the party affiliations (membership,
    leadership) are deleted and an appropriate message is posted to the party
    matchmaking channel.
    """

    party = await Party.from_party_message(rp.message)
    channel = party.channel
    if party.leader != rp.member and not checks.is_admin(rp.member):
        await rp.message.remove_reaction(Emojis.NO_ENTRY_SIGN, rp.member)
        return
    if rp.member != party.leader:
        message = await channel.send(
            f"> {rp.member.mention} has just force "
            f"closed {party.leader.mention}'s party!"
        )
    else:
        message = await channel.send(
            f"> {rp.member.mention} has just " f"disbanded their party!\n"
        )
    await rp.message.delete()
    for m in party.members:
        db.party_channels[channel.id].clear_party_message_of_user(m)
    db.party_channels[channel.id].clear_party_message_of_user(party.leader)
    scheduling.message_delayed_delete(message)


async def start_party(rp: ReactionPayload) -> None:
    """
    Emoji handler that implements the party creation feature.

    If the reacting member is already part of another party, either as member
    or leader, an error message is printed and the emoji is removed.
    """

    await rp.message.remove_reaction(Emojis.TADA, rp.member)
    channel = rp.channel
    if channel.id not in db.party_channels:
        # this happens if the channel got deactivated but
        # the menu wasn't deleted
        delete_message = await channel.send(
            f"Channel has not been configured " f"for party matchmaking"
        )
        scheduling.message_delayed_delete(delete_message)
        return
    channel_info = db.party_channels[channel.id]

    if await channel_info.get_party_message_of_user(rp.member) is not None:
        delete_message = await channel.send(
            f"{rp.member.mention}, you are "
            f"already in another party! "
            f"Leave that party before trying "
            f"to create another one."
        )
        scheduling.message_delayed_delete(delete_message)
        return

    max_slots = channel_info.max_slots
    party = Party(channel, rp.member, max_slots - 1)
    message = await channel.send(embed=party.to_embed())
    await message.add_reaction(Emojis.WHITE_CHECK_MARK)
    await message.add_reaction(Emojis.FAST_FORWARD)
    await message.add_reaction(Emojis.NO_ENTRY_SIGN)
    channel_info.set_party_message_of_user(rp.member, message)


async def handle_party_emptied(
    matchmaking_channel_id: int, voice_channel: discord.VoiceChannel
) -> None:
    """
    Called when a party voice channel emptied out.

    Will delete channel if it is older than the grace period defined in
    `config.PARTY_CHANNEL_GRACE_PERIOD_SECONDS`.
    """

    # grace period for new channels
    if voice_channel.id in scheduling.channel_ids_grace_period:
        return

    await voice_channel.delete()
    db.party_channels[matchmaking_channel_id].active_voice_channels.remove(
        voice_channel.id
    )


def _user_snowflake_to_id(snowflake: str) -> int:
    """
    Extracts the user ID from a user mention in snowflake notation.
    """

    if snowflake[2] == "!":
        return int(snowflake[3:-1])
    else:
        return int(snowflake[2:-1])
