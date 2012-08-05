from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin

import json
import django_tables2 as tables
from django_tables2.utils import A

from lib.views import JSONView
from lib.columns import SystemItemPriceColumn
from core.models import *
from capsuler.models import UserPilot
from eve.ccpmodels import MapSolarsystem, \
        InvMarketgroup, \
        InvType
from evecentral import EveCentral
from celery.execute import send_task
from tasks.tasks import *
from tasks.views import *

class MineralTable(tables.Table):
    typename = tables.LinkColumn('item_details', args=[A('typename')], verbose_name='Item')
    jitaprice = SystemItemPriceColumn(verbose_name='price')
    class Meta:
        attrs = {'class': 'table table-condensed table-bordered table-striped'}
        orderable = False
        template = 'core/armada_table.html'
class ArmadaView(TaskViewletsView):
    template_name = 'core/index.html'

    def viewlets(self):
        pilot_list = Viewlet()
        pilot_list.hook('core/index_pilot_list.html',
                'tasks.fetch_character_sheet',
                '/core/tasks/pilotlist/',
                r'^tasks/pilotlist/(?P<taskid>.+)/$',
                login_required=True)
        self.add_viewlet('pilot_list', pilot_list)

    def get(self, request):
        minerals = InvType.objects.filter(group=InvMarketgroup.objects.get(marketgroupname='Minerals')).order_by('pk').exclude(typename='Chalcopyrite')
        mineral_table = MineralTable(minerals)
        if request.user.is_authenticated():
            capsuler = request.user.get_profile()
            pilots = UserPilot.objects.filter(user=capsuler, activated=True)
            if pilots.count() > 0:
                pilots_task = self.get_viewlet('pilot_list').enqueue(request,
                        {'pilots': pilots},
                        (capsuler.pk,),
                        expires=60)
            else:
                pilots_task = None
        else:
            pilots_task = None


        return self.render_to_response({
            'mineral_table': mineral_table,
            'pilots_task': pilots_task,
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

