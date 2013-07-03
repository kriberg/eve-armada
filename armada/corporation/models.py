from django.db import models
from django.contrib import admin

from armada.capsuler.models import UserPilot, \
    UserCorporation, \
    Capsuler, \
    UserAPIKey
from armada.lib.evemodels import get_location_name
from armada.eve.ccpmodels import InvType, \
        InvFlag
from armada.eve.models import Corporation

class CorporationSetting(models.Model):
    corporation = models.ForeignKey(UserCorporation)
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200, blank=True, default='')

admin.site.register(CorporationSetting)
