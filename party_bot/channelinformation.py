import database
import discord
import sys


class ChannelInformation():
    '''Contains the relevant information about an active channel.'''

    def __init__(self, game_name, channel, max_slots, channel_above):
        # Store all objects as their IDs to allow easier serialization
        self.game_name = game_name
        self.__channel_id = channel.id
        self.max_slots = max_slots
        self.__channel_above_id = channel_above.id
        self.active_voice_channels = set()
        self.voice_channel_counter = 0
        self.__active_party_members_and_leaders = {}

    def get_channel_above(self, guild):
        return guild.get_channel(self.__channel_above_id)

    async def get_party_message_of_user(self, member):
        channel = member.guild.get_channel(self.__channel_id)
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
