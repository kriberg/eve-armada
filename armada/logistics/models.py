from django.db import models
from django.contrib import admin

from armada.capsuler.models import UserPilot, \
        UserCorporation, \
        UserAPIKey, \
        Capsuler

class LogisticsTeam(models.Model):
    name = models.CharField(max_length=200)
    corporation = models.ForeignKey(UserCorporation)
    creator = models.ForeignKey(UserPilot)
    team_type = models.CharField(max_length=30, choices=(
        ('STOCKER', 'Stocking'),
        ('HAULER', 'Hauling'),
        ('MANUFACTUER', 'Manufacturing'),
        ('FUELER', 'Fueling')))

    def get_members(self):
        return LogisticsTeamMember.objects.filter(team=self).order_by('pilot__public_info__name')

    def get_capsuler_members(self, user):
        pilots = user.get_active_pilots()
        return LogisticsTeamMember.objects.filter(team=self, pilot__in=pilots)

    def get_managers(self):
        return LogisticsTeamMember.objects.filter(team=self,
                manager=True,
                accepted=True)

    def is_member(self, capsuler):
        if self.get_capsuler_members(capsuler).count() > 0 or capsuler == self.manager:
            return True
        else:
            return False

    def is_manager(self, capsuler):
        memberships = LogisticsTeamMember.objects.filter(team=self,
                pilot__in=capsuler.get_pilots_in_corporation(self.corporation),
                accepted=True,
                manager=True)
        return memberships.count() > 0

    def is_creator(self, capsuler):
        for membership in self.get_capsuler_members(capsuler):
            if membership.pilot == self.creator:
                return True
        return False

    def __unicode__(self):
        return self.name

    def get_page_link(self):
        return '/%s/%s/%s/' % (self.team_type.lower(), self.corporation, self.name)

    class Meta:
        unique_together = ('corporation', 'name')

class LogisticsTeamMember(models.Model):
    team = models.ForeignKey(LogisticsTeam)
    pilot = models.ForeignKey(UserPilot, related_name='pilot_userpilot')
    accepted = models.BooleanField(default=False, editable=False)
    manager = models.BooleanField(default=False)
    god = models.ForeignKey(Capsuler, related_name='god_capsuler', editable=False)

    class Meta:
        unique_together = ('team', 'pilot')

    def __unicode__(self):
        return '%s: %s' % (self.team.name, self.pilot)

admin.site.register(LogisticsTeam)
admin.site.register(LogisticsTeamMember)
