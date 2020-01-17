import asyncio
import config
import discord
import pytz
import sys
import transaction
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

# tracks channels that are not to be deleted because they're within grace period
# held in memory because persistency is not necessary
channel_ids_grace_period = set()

jobstores = {
    'default': SQLAlchemyJobStore(
        url='sqlite:///' + config.SCHEDULER_DB_FILENAME)
}

_scheduler = None

def init_scheduler():
    '''Initializes the scheduler. Must be run **after**
    config has been initialized.'''
    sys.stdout.write("Starting scheduler...")
    global _scheduler
    _scheduler = AsyncIOScheduler(jobstores=jobstores,
            job_defaults={
                'misfire_grace_time': None
            }
    )
    _scheduler.start()
    sys.stdout.write("done\n")

def message_delayed_delete(message, delay=config.MESSAGE_DELETE_DELAY_SECONDS):
    return delayed_execute(_message_delayed_delete,
            [message.id, message.channel.id],
            timedelta(seconds = delay))

async def _message_delayed_delete(message_id, channel_id):
    channel = config.bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    await message.delete()

def channel_start_grace_period(voice_channel, grace_period_seconds,
                                     delete_callback=None,
                                     delete_callback_args=[]):
    channel_ids_grace_period.add(voice_channel)
    delayed_execute(_remove_grace_protection,
                    [voice_channel.id, delete_callback, delete_callback_args],
                    timedelta(seconds=grace_period_seconds))

async def _remove_grace_protection(voice_channel_id, delete_callback,
                                   delete_callback_args):
    voice_channel = config.bot.get_channel(voice_channel_id)

    if voice_channel is not None and len(voice_channel.members) == 0:
        await voice_channel.delete()
        if delete_callback is not None:
            delete_callback(voice_channel, *delete_callback_args)

    channel_ids_grace_period.discard(voice_channel_id)

def delayed_execute(func, args, timedelta):
    exec_time = datetime.now(config.TIMEZONE) + timedelta

    id = _scheduler.add_job(_execute_wrapper, 'date',
            args=[func]+args, run_date = exec_time).id
    return id

# wrap function to include transaction.commit
async def _execute_wrapper(func, *args, **kwargs):
    ret = func(*args, **kwargs)
    if asyncio.iscoroutine(ret):
        ret = await ret
    transaction.commit()
    return ret

def deschedule(job_id):
    _scheduler.remove_job(job_id)

