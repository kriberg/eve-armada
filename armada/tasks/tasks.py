from armada.capsuler.models import *
from armada.corporation.models import *
from armada.eve.models import *
from armada.lib.api import private, public

from datetime import datetime
from traceback import format_exc

from celery.task import task
#
# Tasks
#

TASK_TIMERS = {'tasks.fetch_character_sheet': 300,
        'tasks.fetch_character_assets': 3600,
        'tasks.fetch_corporate_assets': 3600,
        'tasks.fetch_alliance_list': 86400,
        }

@task(name='tasks.fetch_character_sheet', expires=600)
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
        except Exception, ex:
            #TODO: log this
            print format_exc(ex)
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

@task(name='tasks.fetch_character_assets', expires=600)
def fetch_character_assets(pilot_id):
    try:
        pilot = UserPilot.objects.get(pk=pilot_id, activated=True)
    except:
        return
#   fetch_character_assets.update_state(state='PROGRESS',
#           meta={'pilot': pilot.public_info.name, 'step': 'Fetching from API', 'state': 'PROGRESS'})
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
    except Exception, ex:
        #TODO: log this
        print format_exc(ex)
        raise Exception('Could not retrieve character asset list')
    try:
        cache.cache_time = datetime.fromtimestamp(apidata._meta.cachedUntil)
    except:
        cache.cache_time = datetime.now()
    cache.save()
#   fetch_character_assets.update_state(state='PROGRESS',
#           meta={'pilot': pilot.public_info.name, 'step': 'Parsing asset list', 'state': 'PROGRESS'})

    Asset.objects.delete_pilot_assets(pilot)
    Asset.objects.update_from_api(apidata.assets, pilot)
#   fetch_character_assets.update_state(state='SUCCESS',
#           meta={'pilot': pilot.public_info.name, 'step': 'Completed', 'state': 'SUCCESS'})

@task(name='tasks.fetch_corporate_assets', expires=600)
def fetch_corporate_assets(apikey_id, user_corp_id):
    try:
        apikey = UserAPIKey.objects.get(pk=apikey_id)
        user_corporation = UserCorporation.objects.get(pk=user_corp_id, activated=True)
    except:
        #TODO: log
        print 'not actived', apikey, user_corporation
        return
#   fetch_character_assets.update_state(state='PROGRESS',
#           meta={'corporation': user_corporation.public_info.name, 'step': 'Fetching from API', 'state': 'PROGRESS'})
    try:
        cache = UserAPIKeyCache.objects.get(apikey=apikey,
                function='corp.assetlist')
        if cache.cache_time > datetime.now():
            return
    except UserAPIKeyCache.DoesNotExist:
        cache = UserAPIKeyCache(apikey=apikey,
                function='corp.assetlist')

    try:
        apidata = private.get_corporate_asset_list(apikey.keyid,
                apikey.verification_code)
    except Exception, ex:
        #TODO: log this
        print format_exc(ex)
        raise Exception('Could not retrieve corporation asset list')
    try:
        cache.cache_time = datetime.fromtimestamp(apidata._meta.cachedUntil)
    except:
        cache.cache_time = datetime.now()
    cache.save()
#   fetch_character_assets.update_state(state='PROGRESS',
#           meta={'corporation': user_corporation.public_info.name, 'step': 'Parsing asset list', 'state': 'PROGRESS'})

    CorporationAsset.objects.delete_assets(apikey, user_corporation)
    CorporationAsset.objects.update_from_api(apidata.assets, apikey, user_corporation)
#   fetch_character_assets.update_state(state='SUCCESS',
#           meta={'corporation': user_corporation.public_info.name, 'step': 'Completed', 'state': 'SUCCESS'})

@task(name='tasks.fetch_alliance_list', expires=3600)
def fetch_alliance_list():
    result = public.get_alliance_list()
    print 'Fetched %d alliances...' % len(result.alliances)
    alliances = Alliance.objects.all()
    for alliance in alliances:
        alliance.status = 'Dissolved'
        alliance.save()

    for arow in result.alliances:
        try:
            a = Alliance.objects.get(pk=arow.allianceID)
        except Alliance.DoesNotExist:
            a = Alliance()
        a.id=arow.allianceID
        a.name = arow.name
        a.ticker = arow.shortName
        a.start_date = datetime.fromtimestamp(arow.startDate)
        a.status = 'Active'
        a.executor_corp = arow.executorCorpID
        a.member_count = arow.memberCount
        a.save()

        for member in arow.memberCorporations:
            try:
                am = AllianceMembership.objects.get(corporationid=member.corporationID,
                        allianceid=arow.allianceID)
            except AllianceMembership.DoesNotExist:
                am = AllianceMembership()
                am.allianceid = arow.allianceID
                am.alliance_name = arow.name
                am.corporationid = member.corporationID
                am.start_date = datetime.fromtimestamp(member.startDate)
                am.valid = True
                am.save()
        #TODO: print 'Added %s with %d member corps' % (a.name, len(arow.memberCorporations))
    print 'Alliance list processed'

@task(name='tasks.fetch_conquerable_outposts', expires=3600)
def fetch_conquerable_outposts():
    result = public.get_conquerable_station_list()
    print 'Fetched %d outposts...' % len(result.outposts)

    for outpost in result.outposts:
        try:
            try:
                station = ConquerableStation.objects.get(pk=outpost.stationID)
            except ConquerableStation.DoesNotExist:
                station = ConquerableStation(pk=outpost.stationID)

            station.solarsystem = MapSolarsystem.objects.get(pk=outpost.solarSystemID)
            station.corporationid = outpost.corporationID
            station.stationtype = InvType.objects.get(pk=outpost.stationTypeID)
            station.name = outpost.stationName
            station.save()
            #TODO: print '%s owned by %s at %s' % (station.name, station.owner, station.solarsystem)
        except Exception, e:
            print 'Could not save station %d' % outpost.stationID
            print format_exc(e)
            pass
    print 'Outpost list processed'
