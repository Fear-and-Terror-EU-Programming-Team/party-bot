import config
import jsonpickle
import os

def load():
    '''Returns the database containing a (Channel ID) -> (ChannelInformation)
    mapping.'''
    if not os.path.exists(config.DATABASE_FILENAME):
        save({}) # empty DB
    with open(config.DATABASE_FILENAME, "r") as f:
        raw_db = jsonpickle.loads(f.read())

    # json converts our int keys into string keys, have to undo that here
    db = {
        int(k): v
        for k, v in raw_db.items()
    }
    return db


def save(db):
    '''Saves the specified database.

    The database has to be a (Channel ID) -> (ChannelInformation) mapping.
    '''
    jsonpickle.set_encoder_options("simplejson", indent=4, sort_keys=True)
    with open(config.DATABASE_FILENAME, "w") as f:
        f.write(jsonpickle.dumps(db))
