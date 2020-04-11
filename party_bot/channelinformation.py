'''
This module contains the class definitions of the database objects that are
used to describe channels in which any of the bot's features are activated.
'''

import database
import discord
import persistent
import sys
from BTrees.OOBTree import TreeSet


async def fetch_reference_channel(reference_channel_id, guild):
    # ugly hack to avoid cache inconsistency
    # and work around the APIs broken position data
    #
    # the API can give us positions with gaps but editing any position
    # will first compact the existing positions and then apply the edit
    #
    # this can cause position edits to miss by one
    # to fix this, we collect all VCs and then get their compacted position
    channels = guild.voice_channels
    seen_vcs = []
    ref_channel = None
    for c in channels:
        seen_vcs.append((c.position, c))
        if c.id == reference_channel_id:
            ref_channel = (c.position, c)

    sorted_vc_list = sorted(seen_vcs,
                            # It is possible for two VCs to have the same
                            # position value (WTF?), so we use IDs as
                            # secondary sorting key
                            key=lambda tup: (tup[0], tup[1].id))
    ref_channel_compacted_pos = sorted_vc_list.index(ref_channel)
    return (ref_channel[1], ref_channel_compacted_pos)


class _BaseChannelInformation(persistent.Persistent):

    def __init__(self, channel, reference_channel):
        self.id = channel.id
        self.__reference_channel_id = reference_channel.id


    # compatibility
    async def fetch_channel_above(self, guild):
        return await fetch_reference_channel(self.__reference_channel_id, guild)
    async def fetch_channel_below(self, guild):
        return await fetch_reference_channel(self.__reference_channel_id, guild)


class PartyChannelInformation(_BaseChannelInformation):
    '''Contains the relevant information about an active channel.'''

    def __init__(self, game_name, channel, max_slots, channel_above,
                 open_parties):
        super(PartyChannelInformation, self).__init__(channel, channel_above)
        # Store all objects as their IDs to allow easier serialization
        self.game_name = game_name
        self.max_slots = max_slots
        self.voice_channel_counter = 1
        self.__active_party_members_and_leaders = \
            persistent.mapping.PersistentMapping()
        self.open_parties = open_parties
        self.active_voice_channels = TreeSet()


    async def get_party_message_of_user(self, member):
        channel = member.guild.get_channel(self.id)
        message_id = self.__active_party_members_and_leaders.get(member.id)
        if message_id == None:
            return None

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound as e:
            print(f"Party message deletion was not tracked!\n"
                  f"- Member: {member}\n"
                  f"- Channel: {channel}\n"
                  f"- Message: {message_id}\n", file=sys.stderr)
            self.clear_party_message_of_user(member)
            message = None

        return message

    def set_party_message_of_user(self, user, message):
        self.__active_party_members_and_leaders[user.id] = message.id

    def clear_party_message_of_user(self, user):
        del self.__active_party_members_and_leaders[user.id]


class GamesChannelInformation(_BaseChannelInformation):

    def __init__(self, channel, channel_below):
        super(GamesChannelInformation, self).__init__(channel, channel_below)
        self.counters = persistent.mapping.PersistentMapping()
        self.channel_owners = persistent.mapping.PersistentMapping()

