from capsuler.models import *
from lib.api import private
from datetime import datetime

from celery.task import task
#
# Tasks
#

TASK_TIMERS = {'capsuler.fetch_character_data': 3600,
        }

@task(name='capsuler.fetch_character_data')
def fetch_character_data(capsuler_id):
    try:
        capsuler = Capsuler.objects.get(pk=capsuler_id)
    except:
        return
    pilots = capsuler.get_active_pilots()
    count = pilots.count()
    for pilot in pilots:
        fetch_character_data.update_state(state='PROGRESS',
                meta={'pilot': pilot.public_info.name, 'total': count, 'step': 'Fetching from API',
                    'state': 'PROGRESS'})
        try:
            cache = UserAPIKeyCache.objects.get(apikey=pilot.apikey,
                    pilot=pilot,
                    function='char.charactersheet')
            if cache.cache_time > datetime.now():
                # The character sheet has been cached so it's been parsed recently
                # Consider the data up to date.
                return
        except UserAPIKeyCache.DoesNotExist:
            cache = UserAPIKeyCache(apikey=pilot.apikey,
                    pilot=pilot,
                    function='char.charactersheet')

        try:
            apidata = private.get_character_sheet(pilot.apikey.keyid,
                    pilot.apikey.verification_code,
                    pilot.id)
        except:
            #TODO: log this
            raise Exception('Could not retrieve character sheet')

        try:
            cache.cache_time = datetime.fromtimestamp(apidata._meta.cachedUntil)
        except:
            cache.cache_time = datetime.now()
        cache.save()

        pilot.date_of_birth = datetime.fromtimestamp(apidata.DoB)
        fetch_character_data.update_state(state='PROGRESS',
                meta={'pilot': pilot.public_info.name, 'total': count, 'step': 'Parsing character sheet',
                    'state': 'PROGRESS'})

        UserPilotProperty.objects.update_pilot_from_api(pilot, apidata)
        UserPilotAugmentor.objects.update_pilot_from_api(pilot, apidata)
        UserPilotSkill.objects.update_pilot_from_api(pilot, apidata)
        UserPilotCertificate.objects.update_pilot_from_api(pilot, apidata)
        pilot.save()
        print 'finished with ', pilot
    print 'task completed'
    fetch_character_data.update_state(state='SUCCESS',
            meta={'total': count, 'state': 'SUCCESS', 'step': 'Completed'})
