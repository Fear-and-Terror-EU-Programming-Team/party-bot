import database
import discord
import sys
from bidict import bidict


class _BaseChannelInformation():

    def __init__(self, channel_above):
        self.__channel_above_id = channel_above.id

    def get_channel_above(self, guild):
        return guild.get_channel(self.__channel_above_id)


class PartyChannelInformation(_BaseChannelInformation):
    '''Contains the relevant information about an active channel.'''

    def __init__(self, game_name, channel, max_slots, channel_above,
                 open_parties):
        super(PartyChannelInformation, self).__init__(channel_above)
        # Store all objects as their IDs to allow easier serialization
        self.game_name = game_name
        self.id = channel.id
        self.max_slots = max_slots
        self.active_voice_channels = set()
        self.voice_channel_counter = 1
        self.__active_party_members_and_leaders = {}
        self.open_parties = open_parties


    async def get_party_message_of_user(self, member):
        channel = member.guild.get_channel(self.id)
        message_id = self.__active_party_members_and_leaders.get(str(member.id))
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
        self.__active_party_members_and_leaders[str(user.id)] = str(message.id)

    def clear_party_message_of_user(self, user):
        del self.__active_party_members_and_leaders[str(user.id)]


class GamesChannelInformation(_BaseChannelInformation):

    def __init__(self, channel_above):
        super(GamesChannelInformation, self).__init__(channel_above)
        self.counters = {}
        self.channel_owners = bidict()

