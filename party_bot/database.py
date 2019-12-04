import config
import jsonpickle
import os

class Database:
    def __init__(self, raw_db):
        self.__raw_db = raw_db


    def party_channels(self):
        return self.__raw_db["party_channel_infos"]

    def games_channels(self):
        return self.__raw_db["games_channel_infos"]

    __DEFAULT_RAW_DB = {
        "party_channel_infos": {},
        "games_channels": {},
    }

    def load():
        '''Returns the database containing a (Channel ID) -> (ChannelInformation)
        mapping.'''
        if not os.path.exists(config.DATABASE_FILENAME):
            save(__DEFAULT_RAW_DB) # empty DB
        with open(config.DATABASE_FILENAME, "r") as f:
            db = jsonpickle.loads(f.read())

        return Database(db)


    def save(self):
        '''Saves the specified database.

        The database has to be a (Channel ID) -> (ChannelInformation) mapping.
        '''
        jsonpickle.set_encoder_options("simplejson", indent=4, sort_keys=True)
        with open(config.DATABASE_FILENAME, "w") as f:
            f.write(jsonpickle.dumps(self.__raw_db))
