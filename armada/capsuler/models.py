from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.db.models import Sum

from datetime import datetime

from eve.models import Corporation, \
        Character
from eve.ccpmodels import InvType, \
        CrtCertificate, \
        DgmTypeattribute
from lib.api import private
from lib.evemodels import get_location_name


class Capsuler(models.Model):
    user = models.OneToOneField(User)

    def get_api_keys(self):
        return UserAPIKey.objects.filter(user=self)
    def get_pilots(self):
        return UserPilot.objects.filter(user=self, apikey__in=self.get_api_keys())
    def get_active_pilots(self):
        return UserPilot.objects.filter(user=self,
                apikey__in=self.get_api_keys(),
                activated=True).order_by('public_info__name')
    def fetch_character_names(self):
        characters = []
        for apikey in self.get_api_keys():
            result = private.get_account_characters(apikey.keyid,
                    apikey.verification_code)
            for character in result.characters:
                characters.append({'name': character.name,
                        'id': character.characterID})
        return characters
    def find_apikey_for_pilot(self, characterid):
        for apikey in self.get_api_keys():
            result = private.get_account_characters(apikey.keyid,
                    apikey.verification_code)
            for character in result.characters:
                if str(character.characterID) == str(characterid):
                    return apikey
        raise Exception('No matching apikey for selected character is availble.')
    def __unicode__(self):
        return self.user.username
    def pre_delete(self):
        for pilot in self.get_pilots():
            pilot.delete()
        for apikey in self.get_api_keys():
            apikey.delete()

class UserAPIKey(models.Model):
    keyid = models.CharField(max_length=20)
    verification_code = models.CharField(max_length='128')
    user = models.ForeignKey(Capsuler)
    def pre_delete(self):
        pilots = UserPilots.objects.filter(user=self.user, apikey=self)
        for pilot in pilots:
            pilot.delete()
    def __unicode__(self):
        return '%s: %s' % (self.user, self.keyid)
    class Meta:
        permissions = (('use_apikey', 'Use API key'),)



class UserCorporation(models.Model):
    id = models.IntegerField(primary_key=True)
    public_info = models.OneToOneField(Corporation)
    def __unicode__(self):
        return self.public_info.name

class UserPilotManager(models.Manager):
    def activate_pilot(self, capsuler, apikey, characterid):
        available_characters = private.get_account_characters(apikey.keyid,
                apikey.verification_code)
        charids = []
        for character in available_characters.characters:
            charids.append(str(character.characterID))
        if not characterid in charids:
            #TODO somebody trying to hijack a character
            raise Exception('That\'s not your character!')
        public_info = Character.objects.get_character(characterid)

        if not public_info:
            #TODO good exceptions
            raise Exception('Character does not exist')
        try:
            ucorp = UserCorporation.objects.get(pk=public_info.corporationid)
        except UserCorporation.DoesNotExist:
            ucorp = UserCorporation(id=public_info.corporationid,
                    public_info=public_info.corporation)
            ucorp.save()

        try:
            pilot = UserPilot.objects.get(id=characterid,
                    user=capsuler,
                    apikey=apikey)
        except UserPilot.DoesNotExist:
            pilot = UserPilot(id=characterid,
                    user=capsuler,
                    apikey=apikey)
        pilot.activated = True
        pilot.public_info = public_info
        pilot.corporation = ucorp
        pilot.save()

class UserPilot(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(Capsuler)
    apikey = models.ForeignKey(UserAPIKey)
    corporation = models.ForeignKey(UserCorporation)
    public_info = models.OneToOneField(Character)
    date_of_birth = models.DateTimeField(null=True)
    activated = models.BooleanField(default=False)

    objects = UserPilotManager()

    @property
    def alliance(self):
        return self.public_info.alliance
    def __unicode__(self):
        return self.public_info.name

    def get_property(self, key):
        try:
            return UserPilotProperty.objects.get(pilot=self, key=key).value
        except UserPilotProperty.DoesNotExist:
            return None
    def get_skills_by_group(self):
        groups = {}
        group_names = set([skill.skill.marketgroup.marketgroupname for skill in UserPilotSkill.objects.filter(pilot=self).order_by('skill__marketgroup__marketgroupname')])
        for name in group_names:
            groups[name] = UserPilotSkill.objects.filter(pilot=self, skill__marketgroup__marketgroupname=name).order_by('skill__typename')
        return groups
    def get_skill_points(self):
        try:
            return UserPilotSkill.objects.filter(pilot=self).aggregate(Sum('points'))['points__sum']
        except:
            return 'N/A'
    def get_skill_count(self):
        return UserPilotSkill.objects.filter(pilot=self).count()
    def get_skill_at_l5_count(self):
        return UserPilotSkill.objects.filter(pilot=self, level=5).count()

    @models.permalink
    def get_absolute_url(self):
        return reverse('capsuler_pilot_details', kwargs={'name': self.public_info.name})



class UserAPIKeyCache(models.Model):
    apikey = models.ForeignKey(UserAPIKey)
    pilot = models.ForeignKey(UserPilot, null=True)
    cache_time = models.DateTimeField()
    function = models.CharField(max_length=50)

class UserPilotPropertyManager(models.Manager):
    pilot_properties = ('cloneName',
            'cloneSkillPoints',
            'balance',
            'gender')
    pilot_attributes = ('intelligence',
            'memory',
            'charisma',
            'perception',
            'willpower')
#   def get_pilot_attributes(self, pilot):
#       self.get_queryset().
    def update_or_create(self, pilot, key, value):
        try:
            p = self.get(pilot=pilot,
                    key=key)
        except UserPilotProperty.DoesNotExist:
            p = UserPilotProperty(pilot=pilot,
                    key=key)
        p.value = value
        p.save()
    def update_pilot_from_api(self, pilot, apidata):
        for field in self.pilot_properties:
            value = getattr(apidata, field)
            self.update_or_create(pilot, field, value)
        for attribute in self.pilot_attributes:
            value = getattr(apidata.attributes, attribute)
            self.update_or_create(pilot, attribute, value)


class UserPilotProperty(models.Model):
    pilot = models.ForeignKey(UserPilot)
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=200, blank=True)

    objects = UserPilotPropertyManager()

    def __unicode__(self):
        return u'%s.%s' % (self.pilot, self.key)

class UserPilotSkillManager(models.Manager):
    def update_or_create(self, pilot, skill, points, level, published):
        try:
            skill = UserPilotSkill.objects.get(pilot=pilot, skill=skill)
        except UserPilotSkill.DoesNotExist:
            skill = UserPilotSkill(pilot=pilot, skill=skill)
        skill.points = points
        skill.level = level
        skill.published = published
        skill.save()
    def update_pilot_from_api(self, pilot, apidata):
        for skilldata in apidata.skills:
            skill = InvType.objects.get(pk=skilldata.typeID)
            self.update_or_create(pilot,
                    skill,
                    skilldata.skillpoints,
                    skilldata.level,
                    skilldata.published)

class UserPilotSkill(models.Model):
    pilot = models.ForeignKey(UserPilot)
    skill = models.ForeignKey(InvType)
    points = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    published = models.BooleanField(default=True)

    objects = UserPilotSkillManager()
    def __unicode__(self):
        return u'%s.%s' % (self.pilot, self.skill.typename)
    def get_rank(self):
        try:
            return int(DgmTypeattribute.objects.get(type=self.skill, attribute=275).valuefloat)
        except:
            return 'N/A'

class UserPilotCertificateManager(models.Manager):
    def update_pilot_from_api(self, pilot, apidata):
        for certificatedata in apidata.certificates:
            certtype = CrtCertificate.objects.get(pk=certificatedata.certificateID)
            try:
                self.get(pilot=pilot, certificate=certtype)
            except UserPilotCertificate.DoesNotExist:
                cert = UserPilotCertificate(pilot=pilot, certificate=certtype)
                cert.save()

class UserPilotCertificate(models.Model):
    pilot = models.ForeignKey(UserPilot)
    certificate = models.ForeignKey(CrtCertificate)

    objects = UserPilotCertificateManager()

    def __unicode__(self):
        return self.certificate

class UserPilotRole(models.Model):
    pilot = models.ForeignKey(UserPilot)
    roletype = models.CharField(max_length=100)
    roleid = models.IntegerField()
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class UserPilotTitle(models.Model):
    pilot = models.ForeignKey(UserPilot)
    titleid = models.IntegerField()
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class UserPilotAugmentorManager(models.Manager):
    bonustypes = ('charisma',
            'perception',
            'memory',
            'willpower',
            'intelligence')
    def update_pilot_from_api(self, pilot, apidata):
        for bonustype in self.bonustypes:
            try:
                aug = getattr(apidata.attributeEnhancers, '%sBonus' % bonustype)
                name = aug.augmentorName
                value = aug.augmentorValue
                self.update_or_create(pilot,
                        bonustype,
                        name,
                        value)
            except:
                pass
    def update_or_create(self, pilot, bonustype, name, value):
        try:
            augmentor = self.get(pilot=pilot,
                    bonustype=bonustype)
        except UserPilotAugmentor.DoesNotExist:
            augmentor = UserPilotAugmentor(pilot=pilot,
                    bonustype=bonustype)
        augmentor.augmentor = InvType.objects.get(typename=name)
        augmentor.value = value
        augmentor.save()

class UserPilotAugmentor(models.Model):
    pilot = models.ForeignKey(UserPilot)
    bonustype = models.CharField(max_length=50)
    augmentor = models.ForeignKey(InvType)
    value = models.IntegerField()
    objects = UserPilotAugmentorManager()

class AssetManager(models.Manager):
    def update_from_api(self, assets, pilot):
        itemid_list = [a.itemID for a in assets]
        deleted_items = self.filter(owner=pilot).exclude(pk__in=itemid_list)
        deleted_items.delete()
        for a in assets:
            try:
                aobj = self.get(pk=a.itemID, owner=pilot)
            except Asset.DoesNotExist:
                aobj = Asset(id=a.itemID, owner=pilot)
            aobj.locationid = a.locationID
            aobj.quantity = a.quantity
            aobj.flag = a.flag
            aobj.singleton = a.singleton
            try:
                aobj.itemtype = InvType.objects.get(pk=a.typeID)
            except:
                continue
            aobj.save()


    def delete_pilot_assets(self, pilot):
        self.filter(owner=pilot).delete()

class Asset(models.Model):
    id = models.BigIntegerField(primary_key=True)
    itemtype = models.ForeignKey(InvType)
    locationid = models.BigIntegerField(null=True)
    quantity = models.IntegerField()
    flag = models.IntegerField()
    singleton = models.BooleanField()
    owner = models.ForeignKey(UserPilot)

    objects = AssetManager()

    @property
    def location(self):
        return get_location_name(self.locationid)




def create_capsuler_profile(sender, instance, created, **kwargs):
    if created:
        Capsuler.objects.create(user=instance)
post_save.connect(create_capsuler_profile, sender=User)



admin.site.register(Capsuler)
admin.site.register(UserPilot)
admin.site.register(UserPilotProperty)
admin.site.register(UserPilotSkill)
admin.site.register(Asset)
