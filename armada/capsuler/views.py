from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory

from celery.execute import send_task
from datetime import datetime
import json
import django_tables2 as tables
from django_tables2.utils import A

from lib.columns import SystemItemPriceColumn, \
        LocationColumn, \
        ItemColumn

from capsuler.models import *
from tasks.dispatcher import *
from tasks.views import *


class APIView(TemplateResponseMixin, View):
    template_name = 'capsuler/api.html'
    UserAPIKeyFormSet = modelformset_factory(UserAPIKey,
            exclude=('user',),
            extra=1,
            can_delete=True)

    def build_content(self, request):
        apikeys = request.user.get_profile().get_api_keys()
        apiformset = self.UserAPIKeyFormSet(queryset=apikeys)
        return {
                'apiformset': apiformset,
                }

    def get(self, request):
        return self.render_to_response(self.build_content(request))
    def post(self, request):
        apiformset = self.UserAPIKeyFormSet(request.POST)
        if apiformset.is_valid():
            apikeys = apiformset.save(commit=False)
            for apikey in apikeys:
                apikey.user = request.user.get_profile()
                apikey.save()
        else:
            return self.render_to_response({
                'apiformset': apiformset,
                })
        return self.render_to_response(self.build_content(request))


class PilotListView(TemplateResponseMixin, View):
    template_name = 'capsuler/pilot_list.html'

    def build_content(self, request):
        characters = request.user.get_profile().fetch_character_names()
        pilots = request.user.get_profile().get_pilots()
        unactivated_characters = []
        for character in characters:
            if pilots.filter(pk=character['id']).count() == 0:
                unactivated_characters.append(character)

        return {'activated': pilots,
                'unactivated': unactivated_characters}
    def get(self, request):
        return self.render_to_response(self.build_content(request))
    def post(self, request):
        activated_pilots = request.POST.getlist('activated_pilots')
        #TODO: deactivate pilots
        deactivated_pilots = []
        for characterid in activated_pilots:
            apikey = request.user.get_profile().find_apikey_for_pilot(characterid)
            try:
                pilot = UserPilot.objects.get(id=characterid,
                        user=request.user.get_profile(),
                        apikey=apikey)
                pilot.activated = True
                pilot.save()
            except UserPilot.DoesNotExist:
                pilot = UserPilot.objects.activate_pilot(request.user.get_profile(),
                        apikey,
                        characterid)
        return self.render_to_response(self.build_content(request))

class PilotActivateView(View):
    def get(self, request, characterid):
        apikey = request.user.get_profile().find_apikey_for_pilot(characterid)
        handler = UserPilot.objects.activate_pilot(request.user.get_profile(),
                apikey,
                characterid)
        return HttpResponseRedirect('/capsuler/pilots/')

class PilotDeactivateView(View):
    def get(self, request, characterid):
        pilot = get_object_or_404(UserPilot,
                pk=characterid,
                user=request.user.get_profile())
        for key in request.session.keys():
            if key.startswith('tasks'):
                del request.session[key]

        pilot.delete()

        return HttpResponseRedirect('/capsuler/pilots/')

class PilotDetailsSubview(Subview):
    template_name = 'capsuler/pilot_details_chardata.html'
    task_name = 'tasks.fetch_character_sheet'
    sub_url = '/capsuler/tasks/chardata/'
    def build_context(self, request, params):
        pilot = get_object_or_404(UserPilot,
                public_info__name=params['pilotname'],
                user=request.user.get_profile())
        return {'pilot': pilot}
class PilotDetailsView(TemplateResponseMixin, View):
    template_name = 'capsuler/pilot_details.html'
    def get(self, request, name):
        pilot = get_object_or_404(UserPilot,
                public_info__name=name,
                user=request.user.get_profile())

        pilot_details = PilotDetailsSubview().enqueue(request,
                (pilot.user.pk,),
                pilotname=name,
                expires=60)
        return self.render_to_response({
            'pilot': pilot,
            'pilot_details': pilot_details,
            })

class AssetTable(tables.Table):
    itemtype = ItemColumn(verbose_name='Item')
    quantity = tables.Column()
    locationid = LocationColumn(verbose_name='Location')
    jitaprice = SystemItemPriceColumn(verbose_name='Jita Value', record_accessor='itemtype')
    class Meta:
        attrs = {'class': 'table table-condensed table-bordered table-striped'}
        order_by = ('location', 'itemtype__typename')
        orderable = True
        template = 'core/armada_table.html'
class AssetSubview(Subview):
    template_name = 'capsuler/pilot_assets_assetlist.html'
    task_name = 'tasks.fetch_character_assets'
    sub_url = '/capsuler/tasks/assetlist/'
    def build_context(self, request, params):
        pilot = get_object_or_404(UserPilot,
                public_info__name=params['pilotname'],
                user=request.user.get_profile(),
                activated=True)
        assets = Asset.objects.filter(owner=pilot).order_by('locationid', 'itemtype__typename')
        assets_table = AssetTable(assets)
        tables.RequestConfig(request, paginate={'per_page': 100}).configure(assets_table)
        return {'assets_table': assets_table}
class PilotAssetsView(TemplateResponseMixin, View):
    template_name = 'capsuler/pilot_assets.html'

    def get(self, request, name):
        pilot = get_object_or_404(UserPilot,
                public_info__name=name,
                user=request.user.get_profile(),
                activated=True)
        assetlist = AssetSubview().enqueue(request,
                (pilot.pk,),
                pilotname=name,
                expires=60)
        return self.render_to_response({
            'pilot': pilot,
            'assetlist': assetlist,
            })

