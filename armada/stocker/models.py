from django.db import models
from django.contrib import admin
from django.db.models import Sum

from armada.capsuler.models import UserPilot, \
        UserCorporation, \
        UserAPIKey, \
        UserAPIKeyCache, \
        Capsuler
from armada.lib.evemodels import get_location_name, \
        get_location_id
from armada.eve.ccpmodels import InvType, \
        InvFlag
from armada.corporation.models import CorporationAsset

class StockTeam(models.Model):
    name = models.CharField(max_length=50)
    key = models.ForeignKey(UserAPIKey)
    manager = models.ForeignKey(Capsuler)
    corporation = models.ForeignKey(UserCorporation)

    def get_members(self):
        return StockTeamMember.objects.filter(team=self).order_by('pilot__public_info__name')
    def get_groups(self):
        return StockGroup.objects.filter(team=self)
    def get_capsuler_members(self, user):
        pilots = user.get_active_pilots()
        return StockTeamMember.objects.filter(team=self, pilot__in=pilots)
    def is_member(self, capsuler):
        if self.get_capsuler_members(capsuler).count() > 0 or capsuler == self.manager:
            return True
        else:
            return False
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('stockteam_details', (str(self.corporation.public_info.name),
            str(self.name)))
    class Meta:
        unique_together = ('corporation', 'name')

class StockTeamMember(models.Model):
    team = models.ForeignKey(StockTeam)
    pilot = models.ForeignKey(UserPilot, related_name='pilot_userpilot')
    accepted = models.BooleanField(default=False, editable=False)
    god = models.ForeignKey(Capsuler, related_name='god_capsuler', editable=False)

    class Meta:
        unique_together = ('team', 'pilot')

    def __unicode__(self):
        return '%s: %s' % (self.team.name, self.pilot)

class StockGroup(models.Model):
    name = models.CharField(max_length=50)
    team = models.ForeignKey(StockTeam)
    location = models.CharField(max_length=200)
    division = models.ForeignKey(InvFlag, null=True, blank=True)

    def get_items(self):
        return StockGroupItem.objects.filter(group=self).order_by('item__typename')
    def get_location_id(self):
        return get_location_id(self.location)

    def get_members(self):
        return StockTeamMemberGroupAccess.objects.filter(group=self)
    def get_cached_until(self):
        return UserAPIKeyCache.objects.get(function='corp.assetlist',
                apikey=self.team.key).cache_time
    def get_fetch_time(self):
        return UserAPIKeyCache.objects.get(function='corp.assetlist',
                apikey=self.team.key).fetch_time


    @models.permalink
    def get_absolute_url(self):
        return ('stockgroup_view', [str(self.team.corporation.public_info.name),
            str(self.team.name),
            str(self.name)])

    def __unicode__(self):
        return self.name

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
        assets = CorporationAsset.objects.filter(itemtype=self.item,
                key=self.group.team.key,
                owner=self.group.team.corporation,
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


admin.site.register(StockTeam)
admin.site.register(StockTeamMember)
admin.site.register(StockGroup)
admin.site.register(StockGroupItem)
