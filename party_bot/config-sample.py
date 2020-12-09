# Required settings (must be changed)
BOT_TOKEN = "INSERT BOT TOKEN HERE"

# Optional settings (may be changed)
BOT_CMD_PREFIX = "$"
BOT_ADMIN_ROLES = [
    601467946858184704,  # Clan Leader
    458087769303023617,  # Clan Director
    679233922885746698,  # COO
    679234440496545792,  # CTO
    749112652604899419,  # CMO
]
PARTY_CHANNEL_GRACE_PERIOD_SECONDS = 60
GAMES_CHANNEL_GRACE_PERIOD_HOURS = 4
EVENT_CHANNEL_GRACE_PERIOD_HOURS = 4
MESSAGE_DELETE_DELAY_SECONDS = 30
DATABASE_FILENAME = "database.fs"
SCHEDULER_DB_FILENAME = "scheduler-db.sqlite"


#####################################
# DO NOT EDIT BELOW
#####################################

import pytz

TIMEZONE = pytz.timezone("US/Eastern")


def init_config(_bot):
    global bot
    bot = _bot
