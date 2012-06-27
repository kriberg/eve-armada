
from core.models import *
from django.core.management.base import NoArgsCommand
from lib.api import public
from datetime import datetime
from traceback import print_stack



class Command(NoArgsCommand):
    help = "Fetches the alliance list and all member corporations from the API web service."

    def handle_noargs(self, **options):
        alliances = Alliance.objects.all()
        print 'Fetching member corporations for %d alliances' % alliances.count()
        for alliance in alliances:
            print '%s with %d member corps fetched' % (alliance, alliance.members.count())
