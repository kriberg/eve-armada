from django.db import models
from django.contrib import admin
from django.db.models import Sum

from armada.capsuler.models import UserAPIKeyCache, UserAPIKey, Asset
from armada.lib.evemodels import get_location_id
from armada.eve.ccpmodels import InvType, \
        InvFlag
from armada.logistics.models import LogisticsTeam

class StockerSettings(models.Model):
    team = models.ForeignKey(LogisticsTeam)
    key = models.ForeignKey(UserAPIKey, null=True, blank=True)

    def __unicode__(self):
        return "%s settings" % team.name

class StockGroup(models.Model):
    name = models.CharField(max_length=50)
    team = models.ForeignKey(LogisticsTeam)
    location = models.CharField(max_length=200)
    division = models.ForeignKey(InvFlag, null=True, blank=True)
    settings = models.ForeignKey(StockerSettings)

    def get_items(self):
        return StockGroupItem.objects.filter(group=self).order_by('item__typename')

    def get_location_id(self):
        return get_location_id(self.location)

    def get_members(self):
        return self.team.logistics_team.get_members()
    def get_cached_until(self):
        return UserAPIKeyCache.objects.get(function='corp.assetlist',
                apikey=self.settings.key).cache_time
    def get_fetch_time(self):
        return UserAPIKeyCache.objects.get(function='corp.assetlist',
                apikey=self.settings.key).fetch_time

    def get_settings(self):
        return StockerSettings.objects.get(team=self.team)


    @models.permalink
    def get_absolute_url(self):
        return ('stockgroup_view', [str(self.team.corporation.public_info.name),
            str(self.team.name),
            str(self.name)])

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('team', 'name')

class StockGroupItem(models.Model):
    item = models.ForeignKey(InvType)
    item_name = models.CharField(max_length=200)
    group = models.ForeignKey(StockGroup)
    critical_level = models.IntegerField(null=True, blank=True)
    low_level = models.IntegerField(null=True, blank=True)

    def save(self):
        self.item = InvType.objects.get(typename=self.item_name)
        return super(StockGroupItem, self).save()

    def get_amount(self):
        assets = Asset.objects.filter(itemtype=self.item,
                key=self.group.settings.key,
                corporation=self.group.team.corporation,
                locationid=self.group.get_location_id())
        if self.group.division:
            assets.filter(flag=self.group.division)
        aggregation = assets.aggregate(Sum('quantity'))
        if not aggregation['quantity__sum']:
            return 0
        else:
            try:
                return int(aggregation['quantity__sum'])
            except:
                return aggregation['quantity__sum']

    def get_level(self):
        amount = self.get_amount()
        if amount <= self.critical_level:
            return 2
        elif amount <= self.low_level:
            return 1
        else:
            return 0
    def __unicode__(self):
        return '%s - %s - %s' % (self.group.team.name, self.group.name, self.item.typename)

admin.site.register(StockGroup)
admin.site.register(StockGroupItem)
