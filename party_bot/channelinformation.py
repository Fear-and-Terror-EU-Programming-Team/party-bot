import database

class ChannelInformation():
    '''Contains the relevant information about an active channel.'''
    def __init__(self, game_name, channel, subscriber_role,
                 max_slots, channel_above):
        # Store all objects as their IDs to allow easier serialization
        self.game_name = game_name
        self.__channel_id = channel.id
        self.__subscriber_role_id = subscriber_role.id
        self.__current_party_message_id = None
        self.max_slots = max_slots
        self.__channel_above_id = channel_above.id
        self.active_voice_channels = set()
        self.voice_channel_counter = 0

    async def get_current_party_message(self, guild):
        if self.__current_party_message_id == None:
            return None
        return await guild.get_channel(self.__channel_id)\
            .fetch_message(self.__current_party_message_id)

    def unset_current_party_message(self):
        self.__current_party_message_id = None

    def set_current_party_message(self, message):
        self.__current_party_message_id = message.id

    def get_subscriber_role(self, guild):
        return guild.get_role(self.__subscriber_role_id)

    def get_channel_above(self, guild):
        return guild.get_channel(self.__channel_above_id)


async def get_active_party_message(channel):
    db = database.load()
    return await db[channel.id].get_current_party_message(channel.guild)
