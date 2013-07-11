from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin

import json
import django_tables2 as tables
from django_tables2.utils import A

from armada.lib.views import JSONView
from armada.lib.columns import SystemItemPriceColumn, \
        ItemColumn
from armada.core.models import *
from armada.capsuler.models import UserPilot, UserAPIKey
from armada.eve.ccpmodels import MapSolarsystem, \
        InvGroup, \
        InvType
from armada.lib.evecentral import EveCentral
from celery.execute import send_task
from armada.tasks.tasks import *
from armada.tasks.views import Subview

class MineralTable(tables.Table):
    typename = ItemColumn(verbose_name='Item')
    jitaprice = SystemItemPriceColumn(verbose_name='price')
    template_name = 'core/armada_table.html'
    class Meta:
        attrs = {'class': 'table table-condensed table-bordered table-striped'}
        orderable = False
class PilotListSubview(Subview):
    template_name = 'core/index_pilot_list.html'
    sub_url = '/core/tasks/pilotlist/'
    task_name = 'tasks.fetch_character_sheet'
    def build_context(self, request, params):
        capsuler = request.user.get_profile()
        pilots = UserPilot.objects.filter(user=capsuler, activated=True).order_by('date_of_birth')
        return {'pilots': pilots}

class ArmadaView(TemplateResponseMixin, View):
    template_name = 'core/index.html'

    def get(self, request):
        minerals = InvType.objects.filter(group=InvGroup.objects.get(groupname='Mineral')).order_by('pk').exclude(typename='Chalcopyrite')
        mineral_table = MineralTable(minerals)
        if request.user.is_authenticated():
            pilot_list = PilotListSubview().enqueue(request, (request.user.pk,), expires=60)
            num_keys = UserAPIKey.objects.filter(user=request.user.get_profile()).count()
            num_pilots = UserPilot.objects.filter(user=request.user.get_profile(),
                    activated=True).count()
        else:
            pilot_list = ''
            num_keys = None
            num_pilots = None

        return self.render_to_response({
            'mineral_table': mineral_table,
            'pilot_list': pilot_list,
            'num_keys': num_keys,
            'num_pilots': num_pilots,
            })


class PriceView(TemplateResponseMixin, JSONView):
    base_queryset = ItemSystemFloatingPrice.objects.all()
    read_only = True
    template_name = 'core/json.html'
    def get_parameters(self, request):
        if request.method == 'POST':
            items = request.POST.getlist('items[]')
            systems = request.POST.getlist('systems[]')
        elif request.method == 'GET':
            items = request.GET.getlist('items')
            systems = request.GET.getlist('systems')
        return items, systems
    def filter(self, request):
        items, systems = self.get_parameters(request)
        ec = EveCentral()
        ec.get_system_matrix(InvType.objects.filter(pk__in=items),
            MapSolarsystem.objects.filter(pk__in=systems))
        return ItemSystemFloatingPrice.objects.filter(item__in=items,
                system__in=systems)
    def output(self, request, items, systems):
        text = {'prices': []}
        for price in ItemSystemFloatingPrice.objects.filter(item__in=items, system__in=systems):
            text['prices'].append(price.to_dict())
        return self.render_to_response({'json': self.json_encoder.encode(text)})
    def post(self, request, *args, **kwargs):
        items, systems = self.get_parameters(request)
        return self.output(request, items, systems)
    def get(self, request, *args, **kwargs):
        items, systems = self.get_parameters(request)
        return self.output(request, items, systems)

class SystemPriceView(TemplateResponseMixin, JSONView):
    template_name = 'core/json.html'
    def post(self, request, systemid):
        solarsystem = get_object_or_404(MapSolarsystem, pk=systemid)
        items = InvType.objects.filter(id__in=request.POST.getlist('items[]'))
        ec = EveCentral()
        itemprices = ec.get_items_system_price(items, solarsystem)
        text = {}
        for itemprice in itemprices:
            text[itemprice.item.pk] = (itemprice.buy_maximum, itemprice.sell_minimum)
        return self.render_to_response({'json': self.json_encoder.encode(text)})

def armada404(request):
    return render_to_response('core/404.html',
            {},
            context_instance=RequestContext(request))
def armada500(request):
    return HttpResponse('500')
