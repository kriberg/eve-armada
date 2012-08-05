from capsuler.models import *
from lib.api import private
from datetime import datetime

from celery.task import task
#
# Tasks
#

TASK_TIMERS = {'tasks.fetch_character_sheet': 300,
        'tasks.fetch_character_assets': 3600,
        }

@task(name='tasks.fetch_character_sheet')
def fetch_character_sheet(capsuler_id):
    try:
        capsuler = Capsuler.objects.get(pk=capsuler_id)
    except:
        return
    pilots = capsuler.get_active_pilots()
    count = pilots.count()
    for pilot in pilots:
        fetch_character_sheet.update_state(state='PROGRESS',
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
        fetch_character_sheet.update_state(state='PROGRESS',
                meta={'pilot': pilot.public_info.name, 'total': count, 'step': 'Parsing character sheet',
                    'state': 'PROGRESS'})

        UserPilotProperty.objects.update_pilot_from_api(pilot, apidata)
        UserPilotAugmentor.objects.update_pilot_from_api(pilot, apidata)
        UserPilotSkill.objects.update_pilot_from_api(pilot, apidata)
        UserPilotCertificate.objects.update_pilot_from_api(pilot, apidata)
        pilot.save()
    fetch_character_sheet.update_state(state='SUCCESS',
            meta={'total': count, 'state': 'SUCCESS', 'step': 'Completed'})

@task(name='tasks.fetch_character_assets')
def fetch_character_assets(pilot_id):
    try:
        pilot = UserPilot.objects.get(pk=pilot_id, activated=True)
    except:
        return
    fetch_character_assets.update_state(state='PROGRESS',
            meta={'pilot': pilot.public_info.name, 'step': 'Fetching from API', 'state': 'PROGRESS'})
    try:
        cache = UserAPIKeyCache.objects.get(apikey=pilot.apikey,
                pilot=pilot,
                function='char.assetlist')
        if cache.cache_time > datetime.now():
            return
    except UserAPIKeyCache.DoesNotExist:
        cache = UserAPIKeyCache(apikey=pilot.apikey,
                pilot=pilot,
                function='char.assetlist')

    try:
        apidata = private.get_character_asset_list(pilot.apikey.keyid,
                pilot.apikey.verification_code,
                pilot.id)
    except:
        #TODO: log this
        raise Exception('Could not retrieve character asset list')
    try:
        cache.cache_time = datetime.fromtimestamp(apidata._meta.cachedUntil)
    except:
        cache.cache_time = datetime.now()
    cache.save()
    fetch_character_assets.update_state(state='PROGRESS',
            meta={'pilot': pilot.public_info.name, 'step': 'Parsing asset list', 'state': 'PROGRESS'})

    Asset.objects.update_from_api(apidata.assets, pilot)
    fetch_character_assets.update_state(state='SUCCESS',
            meta={'pilot': pilot.public_info.name, 'step': 'Completed', 'state': 'SUCCESS'})

