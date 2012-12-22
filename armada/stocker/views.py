from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory, inlineformset_factory
from django.core.urlresolvers import reverse

from celery.execute import send_task
from datetime import datetime
import django_tables2 as tables
from django_tables2.utils import A

from armada.tasks.dispatcher import *
from armada.tasks.views import *
from armada.corporation.models import *
from armada.capsuler.models import *
from armada.stocker.models import *
from armada.stocker.forms import *

class Stocker(TemplateResponseMixin, View):
    template_name = 'stocker/stocker_index.html'

    def get(self, request):
        pilots = request.user.get_profile().get_active_pilots()
        managed_teams = StockTeam.objects.filter(manager=request.user.get_profile())
        memberships = StockTeamMember.objects.filter(pilot__in=pilots, accepted=True)
        invitations = StockTeamMember.objects.filter(pilot__in=pilots, accepted=False)
        return self.render_to_response({
            'managed_teams': managed_teams,
            'memberships': memberships,
            'invitations': invitations,
            })

class StockTeamDelete(View):
    def get(self, request, stockteam_id):
        team = get_object_or_404(StockTeam,
                pk=stockteam_id,
                manager=request.user.get_profile())
        team.delete()
        return HttpResponseRedirect(reverse('stocker_index'))

class StockTeamCreate(TemplateResponseMixin, View):
    template_name = 'stocker/stockteam_create.html'

    def get(self, request):
        stockteamform = StockTeamForm()
        stockteamform.fields['key'].queryset = request.user.get_profile().get_corporation_api_keys()
        stockteamform.fields['corporation'].queryset = request.user.get_profile().get_active_corporations()
        return self.render_to_response({
            'stockteamform': stockteamform,
            })
    def post(self, request):
        stockteamform = StockTeamForm(request.POST)
        if stockteamform.is_valid():
            team = stockteamform.save(commit=False)
            # Put in some sanity checks so nobody adds teams for other
            # corps or characters
            capsuler = request.user.get_profile()
            team.manager = capsuler
            if not team.key in capsuler.get_corporation_api_keys() or \
                    not team.corporation in capsuler.get_active_corporations():
                raise Http404('Denied!')
            else:
                team.save()
                return HttpResponseRedirect(reverse('stocker_index'))
        else:
            return self.render_to_response({
                'stockteamform': stockteamform,
                })

class StockTeamUpdate(TemplateResponseMixin, View):
    template_name = 'stocker/stockteam_update.html'
    def post(self, request, stockteam_id):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                pk=stockteam_id,
                manager=capsuler)
        stockteamform = StockTeamUpdateForm(request.POST, instance=team)
        if stockteamform.is_valid():
            team = stockteamform.save(commit=False)
            # Put in some sanity checks so nobody adds teams for other
            # corps or characters
            if not team.key in capsuler.get_corporation_api_keys() or \
                    not team.corporation in capsuler.get_active_corporations() or \
                    not capsuler == team.manager:
                raise Http404('Denied!')
            else:
                team.save()
        else:
            stockteamform.fields['key'].queryset = capsuler.get_corporation_api_keys()
            return self.render_to_response({
                'team': team,
                'stockteamform': stockteamform,
                })
        return HttpResponseRedirect(reverse('stockteam_details', args=(team.corporation.public_info.name,
            team.name)))

class StockTeamDetails(TemplateResponseMixin, View):
    template_name = 'stocker/stockteam_details.html'
    StockTeamMemberFormset = modelformset_factory(StockTeamMember,
            exclude=('team', 'god'),
            can_delete=True)

    def get(self, request, corporation_name, team_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name,
                manager=capsuler)
        memberformset = self.StockTeamMemberFormset(queryset=team.get_members())
        stockteamform = StockTeamUpdateForm(instance=team)
        stockteamform.fields['key'].queryset = capsuler.get_corporation_api_keys()

        return self.render_to_response({
            'team': team,
            'memberformset': memberformset,
            'stockteamform': stockteamform,
            })
    def post(self, request, corporation_name, team_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name,
                manager=capsuler)
        memberformset = self.StockTeamMemberFormset(request.POST)
        stockteamform = StockTeamUpdateForm(instance=team)
        stockteamform.fields['key'].queryset = capsuler.get_corporation_api_keys()

        if memberformset.is_valid():
            memberships = memberformset.save(commit=False)
            for membership in memberships:
                membership.god = capsuler
                membership.team = team
                membership.save()
        memberformset = self.StockTeamMemberFormset(queryset=team.get_members())

        return self.render_to_response({
            'team': team,
            'memberformset': memberformset,
            'stockteamform': stockteamform,
            })

class StockTeamMemberAccept(View):
    def get(self, request, membership_id):
        member = get_object_or_404(StockTeamMember, pk=membership_id,
                pilot__in=request.user.get_profile().get_active_pilots(),
                accepted=False)
        member.accepted = True
        member.save()
        return HttpResponseRedirect(reverse('stocker_index'))

class StockTeamMemberDecline(View):
    def get(self, request, membership_id):
        member = get_object_or_404(StockTeamMember, pk=membership_id,
                pilot__in=request.user.get_profile().get_active_pilots())
        member.delete()
        return HttpResponseRedirect(reverse('stocker_index'))

class StockTeamOverview(TemplateResponseMixin, View):
    template_name = 'stocker/stockteam_overview.html'

    def get(self, request, corporation_name, team_name):
        try:
            corporation = UserCorporation.objects.get_corporation_by_name(corporation_name)
        except UserCorporation.DoesNotExist:
            raise Http404('Unavailable')
        if not corporation.is_member(request.user.get_profile()):
            raise Http404('Unavailable')

        team = get_object_or_404(StockTeam, name=team_name, corporation=corporation)
        members = team.get_capsuler_members(request.user.get_profile())
        if not members.count() > 0:
            raise Http404('Unavailable')

        return self.render_to_response({
            'corporation': corporation,
            'team': team,
            })

class StockGroupViewItemsSubview(Subview):
    template_name = 'stocker/stockgroup_view_items.html'
    task_name = 'tasks.fetch_corporate_assets'
    sub_url = '/stocker/tasks/itemdata/'
    def build_context(self, request, params):
        corporation_name = params['corporation_name']
        team_name = params['team_name']
        group_name = params['group_name']
        try:
            corporation = UserCorporation.objects.get_corporation_by_name(corporation_name)
        except UserCorporation.DoesNotExist:
            raise Http404('Unavailable')
        if not corporation.is_member(request.user.get_profile()):
            raise Http404('Unavailable')

        team = get_object_or_404(StockTeam, name=team_name, corporation=corporation)
        members = team.get_capsuler_members(request.user.get_profile())
        if not members.count() > 0:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup, name=group_name)

        return {'group': group}

class StockGroupView(TemplateResponseMixin, View):
    template_name = 'stocker/stockgroup_view.html'
    def get(self, request, corporation_name, team_name, group_name):
        try:
            corporation = UserCorporation.objects.get_corporation_by_name(corporation_name)
        except UserCorporation.DoesNotExist:
            raise Http404('Unavailable')
        if not corporation.is_member(request.user.get_profile()):
            raise Http404('Unavailable')

        team = get_object_or_404(StockTeam, name=team_name, corporation=corporation)
        members = team.get_capsuler_members(request.user.get_profile())
        if not members.count() > 0:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup, name=group_name)

        stock = StockGroupViewItemsSubview().enqueue(request,
                (group.team.key.pk, corporation.pk),
                corporation_name=corporation_name,
                team_name=team_name,
                group_name=group_name)

        return self.render_to_response({
            'corporation': corporation,
            'team': team,
            'group': group,
            'stock': stock,
            })

class StockGroupCreate(TemplateResponseMixin, View):
    template_name = 'stocker/stockgroup_create.html'

    def get(self, request, corporation_name, team_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name)
        if not team.is_member(capsuler):
            raise Http404('Unavailable')
        stockgroupform = StockGroupForm()
        stockgroupform.fields['division'].queryset = InvFlag.objects.filter(flagname__contains='Office Slot').order_by('pk')
        return self.render_to_response({
            'stockgroupform': stockgroupform,
            'team': team,
            })
    def post(self, request, corporation_name, team_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name)
        if not team.is_member(capsuler):
            raise Http404('Unavailable')

        stockgroupform = StockGroupForm(request.POST)

        if stockgroupform.is_valid():
            stockgroup = stockgroupform.save(commit=False)
            stockgroup.team = team
            stockgroup.save()
            return HttpResponseRedirect(reverse('stockgroup_details', args=(corporation_name,
                team_name,
                stockgroup.name)))
        stockgroupform.fields['division'].queryset = InvFlag.objects.filter(flagname__contains='Office Slot').order_by('flagname')
        return self.render_to_response({
            'stockgroupform': stockgroupform,
            'team': team,
            })

class StockGroupDelete(View):
    def get(self, request, corporation_name, team_name, group_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name)
        if not team.is_member(capsuler) and capsuler != team.manager:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)
        if not capsuler == team.manager:
            raise Http404('Unavailable')
        group.delete()
        return HttpResponseRedirect(reverse('stockteam_details',
            args=(corporation_name, team_name)))

class StockGroupDetails(TemplateResponseMixin, View):
    template_name = 'stocker/stockgroup_details.html'
    StockGroupItemFormset = inlineformset_factory(StockGroup,
            StockGroupItem,
            extra=10,
            can_delete=True,
            form=StockGroupItemForm)

    def get(self, request, corporation_name, team_name, group_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name)
        if not team.is_member(capsuler) and capsuler != team.manager:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)
        if capsuler != team.manager:
            raise Http404('Unavailable')
        itemformset = self.StockGroupItemFormset(instance=group)
        return self.render_to_response({
            'team': team,
            'group': group,
            'itemformset': itemformset,
            })
    def post(self, request, corporation_name, team_name, group_name):
        capsuler = request.user.get_profile()
        team = get_object_or_404(StockTeam,
                corporation__public_info__name=corporation_name,
                name=team_name)
        if not team.is_member(capsuler) and capsuler != team.manager:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)
        if capsuler != team.manager:
            raise Http404('Unavailable')
        itemformset = self.StockGroupItemFormset(request.POST, instance=group)

        if itemformset.is_valid():
            itemformset.save()
            itemformset = self.StockGroupItemFormset(instance=group)

        return self.render_to_response({
            'team': team,
            'group': group,
            'itemformset': itemformset,
            })
