import config
import persistent
import transaction
import sys
import ZODB
from dataclasses import dataclass

class _Database(persistent.Persistent):

    def __init__(self):
        self.party_channels = persistent.mapping.PersistentMapping()
        self.games_channels = persistent.mapping.PersistentMapping()


sys.stdout.write("Starting database...")
connection = ZODB.connection(config.DATABASE_FILENAME)
root = connection.root
if not hasattr(root, "db"):
    database = _Database()
    root.db = database
    transaction.commit()

db = root.db
sys.stdout.write("done\n")
