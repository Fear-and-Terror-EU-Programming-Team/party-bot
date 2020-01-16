# Required settings (must be changed)
BOT_TOKEN = "INSERT BOT TOKEN HERE"

# Optional settings (may be changed)
BOT_CMD_PREFIX  = "!"
                  # GEN, SQ, EFT, MH, R6S
BOT_ADMIN_ROLES  = [521084603457470485, 458084786666340355, 458084949677834250,
                    525348034687664128, 620724711260684288]
PARTY_CHANNEL_GRACE_PERIOD_SECONDS = 60
GAMES_CHANNEL_GRACE_PERIOD_HOURS = 4
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
