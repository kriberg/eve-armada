from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.db.models import Sum

from datetime import datetime
from traceback import format_exc

from armada.eve.models import Corporation, \
        Character
from armada.eve.ccpmodels import InvType, \
        CrtCertificate, \
        DgmTypeattribute, \
        InvFlag
from armada.lib.api import private
from armada.lib.evemodels import get_location_name


class Capsuler(models.Model):
    user = models.OneToOneField(User)

    def get_api_keys(self):
        return UserAPIKey.objects.filter(user=self)

    def get_character_api_keys(self):
        return UserAPIKey.objects.filter(user=self, keytype__in=('Character', 'Account'))

    def get_corporation_api_keys(self):
        return UserAPIKey.objects.filter(user=self, keytype='Corporation')

    def get_pilots(self):
        return UserPilot.objects.filter(user=self, apikey__in=self.get_character_api_keys())

    def get_pilots_in_corporation(self, corporation):
        return UserPilot.objects.filter(user=self,
                corporation=corporation, activated=True)

    def get_active_pilots(self):
        return UserPilot.objects.filter(user=self,
                apikey__in=self.get_api_keys(),
                activated=True).order_by('date_of_birth')

    def get_active_corporations(self):
        pilots = self.get_active_pilots()
        return UserCorporation.objects.filter(activated=True, pk__in=[pilot.corporation.pk for pilot in pilots])

    def has_director_access(self, corporation):
        if type(corporation) == UserCorporation:
            corporation_name = corporation.public_info.name
        else:
            corporation_name = corporation
        for key in self.get_corporation_api_keys():
            if corporation_name == key.get_corporation().name:
                return True
        return False

    def has_member_in_active_corporation(self, corporation_name):
        pilots = self.get_active_pilots()
        if UserCorporation.objects.filter(activated=True,
                public_info__name=corporation_name,
                pk__in=[pilot.corporation.pk for pilot in pilots]).count() > 0:
            return True
        else:
            return False

    def get_inactive_corporations(self):
        pilots = self.get_active_pilots()
        return UserCorporation.objects.filter(activated=False, pk__in=[pilot.corporation.pk for pilot in pilots])

    def fetch_character_names(self):
        characters = []
        for apikey in self.get_character_api_keys():
            result = private.get_account_characters(apikey.keyid,
                    apikey.verification_code)
            for character in result.characters:
                characters.append({'name': character.name,
                        'id': character.characterID})
        return characters

    def find_api_key_for_pilot(self, characterid):
        for apikey in self.get_character_api_keys():
            result = private.get_account_characters(apikey.keyid,
                    apikey.verification_code)
            for character in result.characters:
                if str(character.characterID) == str(characterid):
                    return apikey
        raise Exception('No matching apikey for selected character is availble.')

    def find_api_keys_for_corporation(self, corporation):
        if type(corporation) == UserCorporation:
            corporation = UserCorporation.public_info
        elif type(corporation) == unicode or type(corporation) == str:
            corporation = Corporation.objects.get_corporation(corporation)

        valid_keys = []
        for key in self.get_corporation_api_keys():
            if key.get_corporation() == corporation:
                valid_keys.append(key)
        return UserAPIKey.objects.filter(user=self,
                pk__in=[k.pk for k in valid_keys])

    def __unicode__(self):
        return self.user.username

    def pre_delete(self):
        for pilot in self.get_pilots():
            pilot.delete()
        for apikey in self.get_api_keys():
            apikey.delete()


class UserAPIKey(models.Model):
    KEY_TYPES = (
            ('Account', 'Account'),
            ('Character', 'Character'),
            ('Corporation', 'Corporation'))
    name = models.CharField(max_length=50)
    keyid = models.CharField(max_length=20)
    verification_code = models.CharField(max_length='128')
    keytype = models.CharField(max_length=11, choices=KEY_TYPES, editable=False)
    accessmask = models.CharField(max_length=20, editable=False)
    expires = models.DateTimeField(null=True, editable=False)
    user = models.ForeignKey(Capsuler)

    def pre_delete(self):
        pilots = UserPilots.objects.filter(user=self.user, apikey=self)
        for pilot in pilots:
            pilot.delete()

    def __unicode__(self):
        return self.name

    def get_characters(self):
        if self.keytype == 'Corporation':
            return []
        characters = []
        result = private.get_account_characters(apikey.keyid,
                apikey.verification_code)
        for character in result.characters:
            characters.append({'name': character.name,
                    'id': character.characterID})
        return characters

    def get_corporation(self):
        if not self.keytype == 'Corporation':
            return None
        try:
            result = private.get_corporation_sheet(self.keyid,
                    self.verification_code)
        except:
            return None
        return Corporation.objects.get_corporation(result.corporationID)

    class Meta:
        permissions = (('use_apikey', 'Use API key'),)


class UserCorporationManager(models.Manager):
    def get_corporation_by_name(self, corporation_name):
        try:
            corporation = Corporation.objects.get_corporation(corporation_name)
            return UserCorporation.objects.get(public_info=corporation)
        except:
            raise UserCorporation.DoesNotExist()
    def get_active_member_corporations(self, user):
        pilots = user.get_active_pilots()
        return UserCorporation.objects.filter(activated=True,
                corporation__in=[pilot.corporation for pilot in pilots])

class UserCorporation(models.Model):
    id = models.IntegerField(primary_key=True)
    public_info = models.OneToOneField(Corporation)
    activated = models.BooleanField(default=False)

    objects = UserCorporationManager()

    def __unicode__(self):
        return self.public_info.name

    def is_member(self, capsuler):
        for pilot in capsuler.get_active_pilots():
            if pilot.corporation == self:
                return True
        return False

    def is_director(self, capsuler):
        return capsuler.has_director_access(self)

    def get_active_capsulers(self):
        capsuler_pks = [pilot.user.pk for pilot in UserPilot.objects.filter(activated=True, corporation=self)]
        return Capsuler.objects.filter(pk__in=capsuler_pks)

    def get_active_directors(self):
        # This is a really slow manner to find directors
        directors = []
        for capsuler in self.get_active_capsulers():
            if self.is_director(capsuler):
                directors.append(capsuler)
        return directors



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
        groups = []
        group_names = set([skill.skill.marketgroup.marketgroupname for skill in UserPilotSkill.objects.filter(pilot=self).order_by('skill__group__groupname')])
        for name in group_names:
            group_skills = UserPilotSkill.objects.filter(pilot=self, skill__marketgroup__marketgroupname=name).order_by('skill__typename')
            groups.append((name, {'name': name,
                    'skills': group_skills,
                    'count': group_skills.count(),
                    'skillpoints': group_skills.aggregate(Sum('points'))['points__sum']}))
        groups.sort(key=lambda x: x[0])
        return groups

    def get_skill_points(self):
        try:
            return UserPilotSkill.objects.filter(pilot=self).aggregate(Sum('points'))['points__sum']
        except:
            return 'N/A'

    def get_skill_count(self):
        return UserPilotSkill.objects.filter(pilot=self).count()

    def get_skills_in_group_count(self, group):
        UserPilotSkill.object.filter(pilot=self, skill__marketgroup__marketgroupname=group).count()

    def get_skill_at_l5_count(self):
        return UserPilotSkill.objects.filter(pilot=self, level=5).count()

    def corporation_change(self, old_corp, new_corp):
        # Whenever a pilot changes corporation, we have to drop
        # roles in armada. We'll be aggressive with removing rights

        # Removing logi access
        LogisticsTeamMember.objects.filter(pilot=self).delete()

        #TODO: some notification

    def get_skill_in_training(self):
        return private.get_skill_in_training(self.apikey.keyid,
                self.apikey.verification_code,
                self.pk)

    @models.permalink
    def get_absolute_url(self):
        return reverse('capsuler_pilot_details', kwargs={'name': self.public_info.name})



class UserAPIKeyCache(models.Model):
    apikey = models.ForeignKey(UserAPIKey)
    pilot = models.ForeignKey(UserPilot, null=True)
    cache_time = models.DateTimeField()
    fetch_time = models.DateTimeField(auto_now=True)
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
    def get_skill_points_for_level_5(self):
        # base_points = {1: 250, 2: 1415, 3: 8000, 4: 45255, 5: 256000}
        return 256000*self.get_rank()

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
    def update_from_api(self, assets, key, pilot=None, corporation=None, parent=None):
        for a in assets:
            aobj = Asset(assetid=a.itemID,
                    pilot=pilot,
                    corporation=corporation,
                    key=key)
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
                self.update_from_api(a.contents, key, pilot=pilot, corporation=corporation, parent=aobj)

    def delete_pilot_assets(self, pilot, apikey):
        self.filter(pilot=pilot, key=apikey).delete()

    def delete_corporation_assets(self, corporation, apikey):
        self.filter(corporation=corporation, key=apikey).delete()


class Asset(models.Model):
    assetid = models.BigIntegerField()
    itemtype = models.ForeignKey(InvType)
    locationid = models.BigIntegerField(null=True)
    quantity = models.IntegerField()
    flag = models.ForeignKey(InvFlag)
    singleton = models.BooleanField()
    parent = models.ForeignKey('Asset', null=True, related_name='container')
    pilot = models.ForeignKey(UserPilot, null=True)
    corporation = models.ForeignKey(UserCorporation, null=True)
    key = models.ForeignKey(UserAPIKey)

    objects = AssetManager()

    @property
    def location(self):
        return get_location_name(self.locationid)


def create_capsuler_profile(sender, instance, created, **kwargs):
    if created:
        Capsuler.objects.create(user=instance)
post_save.connect(create_capsuler_profile, sender=User)

admin.site.register(Capsuler)
admin.site.register(UserAPIKey)
admin.site.register(UserCorporation)
admin.site.register(UserPilot)
admin.site.register(UserPilotProperty)
admin.site.register(UserPilotSkill)
admin.site.register(Asset)
