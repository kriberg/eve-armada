from datetime import datetime
from traceback import format_exc

from django.db import models
from settings import STATIC_URL
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

from eve.ccpmodels import *
from lib.api.public import get_corporation_sheet, \
        get_character_sheet, \
        get_names_to_ids


class CharacterManager(models.Manager):
    def get_character(self, character):
        try:
            if type(character) in (unicode, str) and not character.isdigit():
                try:
                    character = Character.objects.get(name=character).pk
                except Character.DoesNotExist:
                    characterid = get_names_to_ids(character)[character]
            else:
                characterid = character
        except:
            raise Character.DoesNotExist
        try:
            char = self.get_query_set().get(pk=characterid)
            cache_time = (datetime.now()-char.timestamp).total_seconds()
            if cache_time > 24*60*60:
                try:
                    char = self.update_from_api(char)
                except:
                    char.save()
                return char
            else:
                return char
        except Character.DoesNotExist:
            try:
                char = Character(id=characterid)
                char = self.update_from_api(char)
                return char
            except Exception, ex:
                print format_exc(ex)
                raise Character.DoesNotExist
    def update_from_api(self, character):
        rs = get_character_sheet(character.id)
        character.load_from_apidata(rs)
        character.save()
        return character

class Character(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=250)
    race = models.ForeignKey(ChrRace, null=True)
    bloodline = models.ForeignKey(ChrBloodline, null=True)
    corporationid = models.IntegerField(null=True)
    corporation_name = models.CharField(max_length=500, blank=True)
    corporation_date = models.DateTimeField(null=True)
    allianceid = models.IntegerField(null=True)
    alliance_date = models.DateTimeField(null=True)
    alliance_name = models.CharField(max_length=500, blank=True)
    security_status = models.DecimalField(default=0.0, max_digits=20, decimal_places=18, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def corporation(self):
        try:
            return Corporation.objects.get_corporation(self.corporationid)
        except:
            return {'name': self.corporation_name, 'pk': self.corporationid}
    @property
    def alliance(self):
        try:
            return Alliance.objects.get(pk=self.allianceid)
        except:
            return {'name': self.alliance_name, 'pk': self.allianceid}

    objects = CharacterManager()
    def __unicode__(self):
        return self.name
    def load_from_apidata(self, apidata):
        self.characterid = apidata.characterID
        self.name = apidata.characterName
        self.race = ChrRace.objects.get(racename=apidata.race)
        self.bloodline = ChrBloodline.objects.get(bloodlinename=apidata.bloodline)
        self.corporationid = apidata.corporationID
        self.corporation_date = datetime.fromtimestamp(apidata.corporationDate)
        self.corporation_name = apidata.corporation
        try:
            self.allianceid = apidata.allianceID
            self.alliance_date = datetime.fromtimestamp(apidata.allianceDate)
            self.alliance_name = apidata.alliance
        except:
            pass
        self.security_status = apidata.securityStatus
        if self.allianceid:
            try:
                am = AllianceMembership.objects.get(corporationid=self.corporationid,
                        allianceid=self.allianceid,
                        valid=True)
                if am.start_date != self.alliance_date:
                    am.start_date = self.alliance_date
                    am.save()
            except AllianceMembership.DoesNotExist:
                if int(apidata.allianceID) > 0:
                    am = AllianceMembership()
                    am.corporationid = apidata.corporationID
                    am.corporation_name = apidata.corporation
                    am.allianceid = apidata.allianceID
                    am.alliance_name = apidata.alliance
                    am.start_date = datetime.fromtimestamp(apidata.allianceDate)
                    am.valied = True
                    am.save()

class Alliance(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=500)
    ticker = models.CharField(max_length=50, blank=True)
    start_date = models.DateTimeField()
    status = models.CharField(max_length=10, default='Active')
    executor_corp = models.IntegerField(null=True)
    member_count = models.IntegerField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
        return self.name
    @property
    def members(self):
        corp_ids = [am.corporationid for am in AllianceMembership.objects.filter(valid=True, allianceid=self.pk)]
        for corp_id in corp_ids:
            Corporation.objects.get_corporation(corp_id)
        return Corporation.objects.filter(id__in=corp_ids)

    def get_dotlan_slug(self):
        return self.name.replace(' ', '_')
    def get_evewho_slug(self):
        return self.name.replace(' ', '+')
    @models.permalink
    def get_absolute_url(self):
        return ('alliance_details', [str(self.name)])


class CorporationManager(models.Manager):
    def get_corporation(self, corporation):
        try:
            if type(corporation) in (unicode, str) and not corporation.isdigit():
                try:
                    corporationid = Corporation.objects.get(name=corporation).pk
                except Corporation.DoesNotExist:
                    corporationid = get_names_to_ids(corporation)[corporation]
            else:
                corporationid = corporation
        except:
            raise Corporation.DoesNotExist
        try:
            corp = self.get_query_set().get(pk=corporationid)
            cache_time = (datetime.now()-corp.timestamp).total_seconds()
            if cache_time > 24*60*60:
                corp.status = 'Dissolved'
                try:
                    corp = self.update_from_api(corp)
                except:
                    corp.save()
                return corp
            else:
                return corp
        except Corporation.DoesNotExist:
            try:
                corp = Corporation(id=corporationid)
                corp = self.update_from_api(corp)
                return corp
            except Exception, ex:
                raise Corporation.DoesNotExist
    def update_from_api(self, corporation):
        rs = get_corporation_sheet(corporation.id)
        corporation.load_from_apidata(rs)
        corporation.save()
        return corporation

class Corporation(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=500, blank=True)
    ticker = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, default='Active')
    ceoid = models.IntegerField(null=True)
    station = models.ForeignKey(StaStation, null=True, related_name='station')
    description = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    tax_rate = models.CharField(max_length=100, blank=True)
    member_count = models.IntegerField(default=0)
    member_limit = models.CharField(max_length=100, blank=True)
    shares = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def alliance(self):
        try:
            am = AllianceMembership.objects.filter(corporationid=self.pk,
                    valid=True).order_by('-start_date')[0]
            return Alliance.objects.get(pk=am.allianceid)
        except AllianceMembership.DoesNotExist:
            return None
        except Alliance.DoesNotExist:
            return am.alliance_name
        except IndexError:
            return None

    @alliance.setter
    def alliance(self, alliance):
        if type(alliance) == int or type(alliance) == str:
            pk = alliance
        else:
            pk = alliance.pk
        try:
            am = AllianceMembership.objects.get(corporationid=self.corporationid,
                    valid=True, allianceid=pk)
        except AllianceMembership.DoesNotExist:
            am = AllianceMembership()
            am.corporationid = self.pk
            am.allianceid = pk
            try:
                am.alliance_name = alliance.name
            except:
                pass
            am.valid = True
            am.start_date = datetime.now()
            am.save()

    @property
    def ceo(self):
        return Character.objects.get_character(self.ceoid)
    def get_dotlan_slug(self):
        return self.name.replace(' ', '_')
    def get_evewho_slug(self):
        return self.name.replace(' ', '+')

    objects = CorporationManager()

    def load_from_apidata(self, apidata):
        self.id = apidata.corporationID
        self.name = apidata.corporationName
        self.ticker = apidata.ticker
        self.description = apidata.description
        if not apidata.allianceID == 0:
            try:
                AllianceMembership.objects.get(valid=True,
                        corporationid=apidata.corporationID,
                        allianceid=apidata.allianceID)
            except AllianceMembership.DoesNotExist:
                am = AllianceMembership()
                am.corporationid = apidata.corporationID
                am.allianceid = apidata.allianceID
                am.alliance_name = apidata.allianceName
                am.start_date = datetime.now()
                am.valid = True
                am.save()
        self.member_count = apidata.memberCount
        self.shares = apidata.shares
        try:
            self.station = StaStation.objects.get(pk=apidata.stationID)
        except:
            #FIXME: save the value for debugging later
            pass
        self.tax_rate = apidata.taxRate
        if not apidata.url:
            self.url = ''
        else:
            self.url = apidata.url
        self.ceoid = apidata.ceoID
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('corporation_details', [str(self.name)])

class AllianceMembership(models.Model):
    corporationid = models.IntegerField()
    corporation_name = models.CharField(max_length=500)
    allianceid = models.IntegerField()
    alliance_name = models.CharField(max_length=200, null=True)
    valid = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True)
    @property
    def alliance():
        try:
            return Alliance.objects.get(pk=self.allianceid)
        except Alliance.DoesNotExist:
            return {'pk': self.allianceid,
                    'name': self.alliance_name}

class ConquerableStation(models.Model):
    id = models.IntegerField(primary_key=True)

class Station(models.Model):
    id = models.IntegerField(primary_key=True)
    npcstation = models.ForeignKey(StaStation, null=True, related_name='station_npcstation')
    conqstation = models.ForeignKey(ConquerableStation, null=True)

class StationManager(models.Manager):
    def get_station(stationid):
        if not type(stationid) == int:
            stationid = int(stationid)
        #if stationid 

class TypeAttributesView(models.Model):
    attribute = models.ForeignKey(DgmAttributetype, primary_key=True, db_column='attributeid')
    type = models.ForeignKey(InvType, db_column='typeid')
    categoryname = models.CharField(max_length=50)
    categorydescription = models.CharField(max_length=200)
    displayname = models.CharField(max_length=100)
    valueint = models.IntegerField()
    valuefloat = models.DecimalField(max_digits=20, decimal_places=2)
    icon = models.ForeignKey(EveIcon, db_column='iconid')

    def __unicode__(self):
        return self.displayname
    class Meta:
        db_table = 'eve_typeattributes_view'
        managed = False
        ordering = ['categoryname','displayname']

