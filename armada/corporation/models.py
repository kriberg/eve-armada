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

class CorporationAssetManager(models.Manager):
    def update_from_api(self, assets, key, owner, parent=None):
        for a in assets:
            aobj = CorporationAsset(assetid=a.itemID, owner=owner, key=key)
            if hasattr(a, 'locationID'):
                aobj.locationid = a.locationID
            elif hasattr(parent, 'locationid'):
                aobj.locationid = parent.locationid
            else:
                #TODO: logthis
                continue
            aobj.quantity = a.quantity
            aobj.singleton = a.singleton
            if parent:
                aobj.parent=parent
            try:
                aobj.itemtype = InvType.objects.get(pk=a.typeID)
            except:
                #TODO: logthis
                continue
            try:
                aobj.flag = InvFlag.objects.get(pk=a.flag)
            except:
                #TODO: logthis
                continue
            aobj.save()
            if hasattr(a, 'contents'):
                self.update_from_api(a.contents, key, owner, parent=aobj)
    def delete_assets(self, apikey, corporation):
        self.filter(owner=corporation, key=apikey).delete()

class CorporationAsset(models.Model):
    assetid = models.BigIntegerField()
    itemtype = models.ForeignKey(InvType)
    locationid = models.BigIntegerField(null=True)
    quantity = models.IntegerField()
    flag = models.ForeignKey(InvFlag)
    singleton = models.BooleanField()
    parent = models.ForeignKey('CorporationAsset', null=True, related_name='container')
    owner = models.ForeignKey(UserCorporation)
    key = models.ForeignKey(UserAPIKey)

    objects = CorporationAssetManager()

    @property
    def location(self):
        return get_location_name(self.locationid)

admin.site.register(CorporationAsset)
admin.site.register(CorporationSetting)
