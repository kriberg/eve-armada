from django.core.management.base import NoArgsCommand
from datetime import datetime
from traceback import print_stack

from armada.eve.models import *
from armada.lib.api import public


class Command(NoArgsCommand):
    help = "Fetches the alliance list and all member corporations from the API web service."

    def handle_noargs(self, **options):
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
            print 'Added %s with %d member corps' % (a.name, len(arow.memberCorporations))

