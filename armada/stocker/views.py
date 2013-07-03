from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory, inlineformset_factory, modelform_factory
from django.core.urlresolvers import reverse

from celery.execute import send_task
from datetime import datetime
import django_tables2 as tables
from django_tables2.utils import A

from armada.tasks.dispatcher import *
from armada.tasks.views import *
from armada.corporation.models import *
from armada.capsuler.models import *
from armada.logistics.models import *
from armada.stocker.models import *
from armada.stocker.forms import *

class StockTeamOverview(TemplateResponseMixin, View):
    template_name = 'stocker/stockteam_overview.html'
    StockerSettingsForm = modelform_factory(StockerSettings, exclude=('team',))

    def get(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_member(capsuler):
            raise PermissionDenied

        try:
            settings = StockerSettings.objects.get(team=team)
        except StockerSettings.DoesNotExist:
            settings = StockerSettings(team=team)
            settings.save()
        manager = team.is_manager(capsuler)
        creator = team.is_creator(capsuler)
        if creator:
            settingsform = self.StockerSettingsForm(instance=settings)
            keys = capsuler.find_api_keys_for_corporation(corp.public_info)
            settingsform.fields['key'].queryset = keys
        else:
            settingsform = None

        groups = StockGroup.objects.filter(team=team).order_by('name')

        return self.render_to_response({
            'team': team,
            'manager': manager,
            'creator': creator,
            'settingsform': settingsform,
            'groups': groups,
            })

    def post(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
            corporation=corp,
            name=team_name)
        if not team.is_member(capsuler):
            raise PermissionDenied

        manager = team.is_manager(capsuler)
        creator = team.is_creator(capsuler)

        if creator:
            try:
                settings = StockerSettings.objects.get(team=team)
            except StockerSettings.DoesNotExist:
                settings = StockerSettings(team=team)
                settings.save()
            settings_form = self.StockerSettingsForm(request.POST, instance=settings)
            if settings_form.is_valid():
                settings = settings_form.save(commit=False)
                settings.team = team
                if settings.key in capsuler.find_api_keys_for_corporation(corp.public_info):
                    settings.save()
        return self.get(request, corporation_name, team_name)


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
            print '1'
            raise Http404('Unavailable')
        if not corporation.is_member(request.user.get_profile()):
            print '2'
            raise Http404('Unavailable')

        team = get_object_or_404(LogisticsTeam, name=team_name, corporation=corporation)
        members = team.get_capsuler_members(request.user.get_profile())
        if not members.count() > 0:
            print '3'
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

        team = get_object_or_404(LogisticsTeam, name=team_name, corporation=corporation)
        members = team.get_capsuler_members(request.user.get_profile())
        if not members.count() > 0:
            raise Http404('Unavailable')
        group = get_object_or_404(StockGroup, name=group_name)

        stock = StockGroupViewItemsSubview().enqueue(request,
                (group.get_settings().key.pk, corporation.pk),
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
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
                corporation=corp,
                name=team_name)
        if not team.is_manager(capsuler):
            raise PermissionDenied

        stockgroupform = StockGroupForm()
        stockgroupform.fields['division'].queryset = InvFlag.objects.filter(flagname__contains='Office Slot').order_by('pk')

        return self.render_to_response({
            'stockgroupform': stockgroupform,
            'team': team,
            })

    def post(self, request, corporation_name, team_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
                corporation=corp,
                name=team_name)
        if not team.is_manager(capsuler):
            raise PermissionDenied

        settings = get_object_or_404(StockerSettings, team=team)
        stockgroupform = StockGroupForm(request.POST)

        if stockgroupform.is_valid():
            stockgroup = stockgroupform.save(commit=False)
            stockgroup.team = team
            stockgroup.settings = settings
            stockgroup.save()
            return HttpResponseRedirect(reverse('stockgroup_details',
                args=(corporation_name, team_name, stockgroup.name)))
        stockgroupform.fields['division'].queryset = InvFlag.objects.filter(flagname__contains='Office Slot').order_by('flagname')
        return self.render_to_response({
            'stockgroupform': stockgroupform,
            'team': team,
            })

class StockGroupDelete(View):
    def get(self, request, corporation_name, team_name, group_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
                corporation=corp,
                name=team_name)
        if not team.is_manager(capsuler):
            raise PermissionDenied

        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)
        group.delete()
        return HttpResponseRedirect(reverse('stockteam_overview',
            args=(corporation_name, team_name)))

class StockGroupDetails(TemplateResponseMixin, View):
    template_name = 'stocker/stockgroup_details.html'
    StockGroupItemFormset = inlineformset_factory(StockGroup,
            StockGroupItem,
            extra=10,
            can_delete=True,
            form=StockGroupItemForm)

    def get(self, request, corporation_name, team_name, group_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
                corporation=corp,
                name=team_name)
        if not team.is_manager(capsuler):
            raise PermissionDenied

        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)

        stockgroupform = StockGroupForm(instance=group)
        stockgroupform.fields['division'].queryset = InvFlag.objects.filter(flagname__contains='Office Slot').order_by('pk')

        itemformset = self.StockGroupItemFormset(instance=group)
        return self.render_to_response({
            'team': team,
            'group': group,
            'itemformset': itemformset,
            'stockgroupform': stockgroupform
            })

    def post(self, request, corporation_name, team_name, group_name):
        corp = get_object_or_404(UserCorporation, public_info__name=corporation_name)
        capsuler = request.user.get_profile()
        team = get_object_or_404(LogisticsTeam,
                corporation=corp,
                name=team_name)
        if not team.is_manager(capsuler):
            raise PermissionDenied

        group = get_object_or_404(StockGroup,
                team=team,
                name=group_name)
        itemformset = self.StockGroupItemFormset(request.POST, instance=group)

        if itemformset.is_valid():
            itemformset.save()
            itemformset = self.StockGroupItemFormset(instance=group)

        stockgroupform = StockGroupForm(request.POST, instance=group)
        if stockgroupform.is_valid():
            stockgroupform.save()

        return self.render_to_response({
            'team': team,
            'group': group,
            'itemformset': itemformset,
            'stockgroupform': stockgroupform
            })
