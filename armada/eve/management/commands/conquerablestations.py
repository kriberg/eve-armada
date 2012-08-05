
from eve.models import *
from django.core.management.base import NoArgsCommand
from lib.api import public
from datetime import datetime
from traceback import format_exc



class Command(NoArgsCommand):
    help = "Fetches the conquerable stations list from the API web service."

    def handle_noargs(self, **options):
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
                print '%s owned by %s at %s' % (station.name, station.owner, station.solarsystem)
            except Exception, e:
                print 'Could not save station %d' % outpost.stationID
                print format_exc(e)


