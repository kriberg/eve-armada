from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory, inlineformset_factory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

from armada.logistics.models import *
from armada.logistics.forms import *

class Logistics(TemplateResponseMixin, View):
    template_name = 'logistics/logistics_index.html'

    def get(self, request, corporation_name):
        if not request.user.get_profile().has_member_in_active_corporation(corporation_name):
            raise PermissionDenied
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)

        pilots = request.user.get_profile().get_pilots_in_corporation(corp)
        memberships = LogisticsTeamMember.objects.filter(pilot__in=pilots,
                team__corporation=corp,
                accepted=True)
        invitations = LogisticsTeamMember.objects.filter(pilot__in=pilots,
                team__corporation=corp,
                accepted=False)
        return self.render_to_response({
            'corporation': corp,
            'memberships': memberships,
            'invitations': invitations,
            'director': corp.is_director(request.user.get_profile()),
            })

class LogisticsTeamCreate(TemplateResponseMixin, View):
    template_name = 'logistics/logisticsteam_create.html'

    def get(self, request, corporation_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        if not corp.is_director(request.user.get_profile()):
            raise PermissionDenied

        logisticsteamform = LogisticsTeamForm()
        corp_pilots = request.user.get_profile().get_pilots_in_corporation(corp)
        logisticsteamform.fields['creator'].queryset = corp_pilots

        return self.render_to_response({
            'corporation': corp,
            'logisticsteamform': logisticsteamform,
            })
    def post(self, request, corporation_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        if not corp.is_director(request.user.get_profile()):
            raise PermissionDenied

        logisticsteamform = LogisticsTeamForm(request.POST)
        corp_pilots = request.user.get_profile().get_pilots_in_corporation(corp)
        logisticsteamform.fields['creator'].queryset = corp_pilots
        if logisticsteamform.is_valid():
            team = logisticsteamform.save(commit=False)
            team.corporation = corp
            if not team.creator in corp_pilots:
                raise PermissionDenied
            team.save()
            manager = LogisticsTeamMember(team=team,
                    pilot=team.creator,
                    accepted=True,
                    manager=True,
                    god=request.user.get_profile())
            manager.save()
            return HttpResponseRedirect(reverse('logistics_index', args=(corp.public_info.name,)))
        else:
            return self.render_to_response({
                'corporation': corp,
                'logisticsteamform': logisticsteamform,
                })

class LogisticsTeamDelete(View):
    def get(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        if not corp.is_director(request.user.get_profile()):
            raise PermissionDenied

        team = get_object_or_404(LogisticsTeam,
            name=team_name,
            corporation=corp)
        if not team.creator in request.user.get_profile().get_pilots_in_corporation(corp):
            raise PermissionDenied
        team.delete()

        return HttpResponseRedirect(reverse('logistics_index', args=(corp.public_info.name,)))

class LogisticsTeamMemberAccept(View):
    def get(self, request, corporation_name, membership_id):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        member = get_object_or_404(LogisticsTeamMember, pk=membership_id,
            pilot__in=request.user.get_profile().get_pilots_in_corporation(corp),
            accepted=False)
        member.accepted = True
        member.save()
        return HttpResponseRedirect(reverse('logistics_index', args=(corp.public_info.name,)))

class LogisticsTeamMemberDecline(View):
    def get(self, request, corporation_name, membership_id):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        member = get_object_or_404(LogisticsTeamMember, pk=membership_id,
            pilot__in=request.user.get_profile().get_pilots_in_corporation(corp))
        member.delete()
        return HttpResponseRedirect(reverse('logistics_index', args=(corp.public_info.name,)))

class LogisticsTeamMembers(TemplateResponseMixin, View):
    template_name = 'logistics/logisticsteam_members.html'
    LogisticsTeamMemberFormset = modelformset_factory(LogisticsTeamMember,
            exclude=('team', 'accepted'), can_delete=True)

    def get(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_manager(request.user.get_profile()):
            raise PermissionDenied

        memberformset = self.LogisticsTeamMemberFormset(queryset=team.get_members())

        return self.render_to_response({
            'team': team,
            'memberformset': memberformset,
            })

    def post(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_manager(request.user.get_profile()):
            raise PermissionDenied

        memberformset = self.LogisticsTeamMemberFormset(request.POST,
                queryset=team.get_members())

        if memberformset.is_valid():
            memberships = memberformset.save(commit=False)
            for membership in memberships:
                membership.god = capsuler
                membership.team = team
                membership.save()
            memberformset = self.LogisticsTeamMemberFormset(queryset=team.get_members())

        return self.render_to_response({
            'team': team,
            'memberformset': memberformset,
            })

class LogisticsTeamDetails(TemplateResponseMixin, View):
    template_name = 'logistics/logisticsteam_details.html'
    def get(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_manager(request.user.get_profile()):
            raise PermissionDenied

        logisticsteamform = LogisticsTeamUpdateForm(instance=team)

        return self.render_to_response({
            'team': team,
            'logisticsteamform': logisticsteamform,
            })

    def post(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_manager(request.user.get_profile()):
            raise PermissionDenied

        logisticsteamform = LogisticsTeamUpdateForm(request.POST, instance=team)
        if logisticsteamform.is_valid():
            team = logisticsteamform.save()

        return self.render_to_response({
            'team': team,
            'logisticsteamform': logisticsteamform,
            })

