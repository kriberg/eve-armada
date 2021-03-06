from django.http import HttpResponse, \
        HttpResponseRedirect, \
        HttpResponseForbidden, \
        Http404, \
        StreamingHttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory
from django.template.defaultfilters import slugify

from celery.execute import send_task
from datetime import datetime
import json
import django_tables2 as tables
from django_tables2.utils import A

from armada.lib.columns import SystemItemPriceColumn, \
        LocationColumn, \
        ItemColumn

from armada.capsuler.models import *
from armada.tasks.dispatcher import *
from armada.tasks.views import *
from armada.capsuler.forms import UserAPIKeyFormSet, UserAPIKeyForm


class APIView(TemplateResponseMixin, View):
    template_name = 'capsuler/api.html'
    UserAPIKeyFormSet = modelformset_factory(UserAPIKey, form=UserAPIKeyForm,
            extra=1, can_delete=True, formset=UserAPIKeyFormSet)

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
                kinfo = apiformset.keydata[apikey.keyid]
                apikey.user = request.user.get_profile()
                apikey.keytype = kinfo['keytype']
                apikey.accessmask = kinfo['accessmask']
                if type(kinfo['expires']) is int:
                    apikey.expires = datetime.fromtimestamp(kinfo['expires'])
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
            apikey = request.user.get_profile().find_api_key_for_pilot(characterid)
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
        apikey = request.user.get_profile().find_api_key_for_pilot(characterid)
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


class PilotDetailsView(TemplateResponseMixin, View):
    template_name = 'capsuler/pilot_details.html'
    def get(self, request, name):
        pilot = get_object_or_404(UserPilot,
                public_info__name=name,
                user=request.user.get_profile())

        return self.render_to_response({
            'pilot': pilot,
            })


class AssetTable(tables.Table):
    itemtype = ItemColumn(verbose_name='Item')
    quantity = tables.Column()
    locationid = LocationColumn(verbose_name='Location')
    jitaprice = SystemItemPriceColumn(verbose_name='Jita Value', record_accessor='itemtype')
    template_name = 'core/armada_table.html'

    class Meta:
        attrs = {'class': 'table table-condensed table-bordered table-striped'}
        order_by = ('location', 'itemtype__typename')
        orderable = True


class AssetsJSONView(View):
    def get(self, request, pilot_id):
        pilot = get_object_or_404(UserPilot,
                pk=pilot_id,
                user=request.user.get_profile(),
                activated=True)

        requested_node = request.GET.get('node', None)
        if not requested_node:
            #assets = Asset.objects.filter(pilot=pilot, key=pilot.apikey,
            #    parent=None).order_by('locationid').distinct('locationid')
            #unique_locations = []
            #for a in assets:
            #    unique_locations.append(a.as_location())
            assets = Asset.objects.get_asset_tree(pilot=pilot,
                    key=pilot.apikey)
            return HttpResponse(json.dumps(assets),
                    content_type='application/json')
        else:
            tree = Asset.objects.get_location_asset_tree(requested_node,
                    pilot=pilot,
                    key=pilot.apikey)
            return HttpResponse(json.dumps(tree),
                    content_type='application/json')


class PilotAssetsView(TemplateResponseMixin, View):
    template_name = 'capsuler/pilot_assets.html'

    def get(self, request, name):
        pilot = get_object_or_404(UserPilot,
                public_info__name=name,
                user=request.user.get_profile(),
                activated=True)
        return self.render_to_response({
            'pilot': pilot,
            })

