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
        PriceColumn
from armada.eve.templatetags.eve_tags import *
from armada.eve.models import *
from armada.eve.ccpmodels import *
from armada.lib.evecentral import EveCentral

class InvTypeJSON(JSONView):
    base_queryset = InvType.objects.filter(published=True)
    page_size = 100
    read_only = True

    def dispatch(self, request, *args, **kwargs):
        return super(InvTypeJSON, self).dispatch(request, *args, **kwargs)

def typeahead_invtype_name(request):
    names = [invtype.typename for invtype in InvType.objects.filter(published=True, volume__gt=0.0)]
    return HttpResponse(json.dumps(names))

class ItemListView(TemplateResponseMixin, View):
    template_name='eve/item_list.html'
    class ItemTable(tables.Table):
        typename = tables.LinkColumn('item_details', args=[A('typename')], verbose_name='Item')
        volume = tables.Column()
        group = tables.Column()
        baseprice = PriceColumn()
        jitaprice = SystemItemPriceColumn(verbose_name='jita price', orderable=False)
        template_name = 'core/armada_table.html'

        class Meta:
            attrs = {'class': 'table table-condensed table-bordered table-striped span12',
                    'id': 'item_table'}
            orderable = True
            order_by = ('name', )
    def filter_items(self, request):
        items = InvType.objects.filter(published=True,
                volume__gt=0.0)
        if request.method == 'POST':
            search_terms = request.POST.get('search-terms', None)
            if search_terms:
                items = items.filter(typename__icontains=search_terms)
                return items, search_terms
        return items, None
    def build_contents(self, request):
        market_groups = InvMarketgroup.objects.filter(parentgroup=None)
        meta_groups = InvMetagroup.objects.all().exclude(id__range=(7,13))
        items, search_terms = self.filter_items(request)
        item_table = self.ItemTable(items)
        tables.RequestConfig(request, paginate={'per_page': 50}).configure(item_table)
        return {
            'market_groups': market_groups,
            'meta_groups': meta_groups,
            'item_table': item_table,
            'search_terms': search_terms,
            }
    def get(self, request):
        return self.render_to_response(self.build_contents(request))
    def post(self, request):
        return self.render_to_response(self.build_contents(request))

class ItemView(TemplateResponseMixin, View):
    template_name='eve/item_details.html'
    def get(self, request, name):
        item = get_object_or_404(InvType, typename=name)
        attributes = TypeAttributesView.objects.filter(type=item).exclude(icon=0).exclude(icon=None).order_by('categoryname', 'displayname')
        attributemap = {}
        for attribute in attributes:
            if not attribute.categoryname in attributemap:
                attributemap[attribute.categoryname] = []
            attributemap[attribute.categoryname].append(attribute)

        systems = MapSolarsystem.objects.filter(solarsystemname__in=('Jita','Rens','Dodixie','Amarr','Hek','Oursulaert','Tash-Murkon Prime')).order_by('solarsystemname')

        return self.render_to_response({
            'item': item,
            'attributemap': attributemap,
            'systems': systems,
            })

class AllianceListView(TemplateResponseMixin, View):
    template_name = 'eve/alliance_list.html'
    class AllianceTable(tables.Table):
        name = tables.LinkColumn('alliance_details', args=[A('name')])
        ticker = tables.Column()
        start_date = tables.Column(verbose_name='established')
        member_count = tables.Column(verbose_name='members')
        template_name = 'core/armada_table.html'
        class Meta:
            attrs = {'class': 'table table-condensed table-bordered table-striped span12'}
            orderable = True
            order_by = ('-member_count', 'name')

    def get(self, request):
        alliance_table = self.AllianceTable(Alliance.objects.all())
        tables.RequestConfig(request, paginate={'per_page': 200}).configure(alliance_table)
        return self.render_to_response({
            'alliance_table': alliance_table}
            )

class AllianceView(TemplateResponseMixin, View):
    template_name = 'eve/alliance_details.html'
    class CorporationTable(tables.Table):
        name = tables.LinkColumn('corporation_details', args=[A('name')])
        ticker = tables.Column()
        joined = None
        member_count = tables.Column(verbose_name='members')
        template_name = 'core/armada_table.html'
        class Meta:
            attrs = {'class': 'table table-condensed table-bordered table-striped span8'}
            orderable = True
            order_by = ('-member_count', 'name')

    def get(self, request, alliance):
        alliance = get_object_or_404(Alliance, name=alliance.replace('_', ' '))
        member_corporations_table = self.CorporationTable(alliance.members)
        tables.RequestConfig(request).configure(member_corporations_table)
        executor_corp = Corporation.objects.get_corporation(alliance.executor_corp)
        return self.render_to_response({
            'alliance': alliance,
            'member_corporations_table': member_corporations_table,
            'executor_corp': executor_corp,
            })

class CorporationView(TemplateResponseMixin, View):
    template_name = 'eve/corporation_details.html'
    def get(self, request, corporation):
        corporation = Corporation.objects.get_corporation(corporation)
        return self.render_to_response({'corporation': corporation})

class CorporationListView(TemplateResponseMixin, View):
    template_name = 'eve/corporation_list.html'
    class CorporationTable(tables.Table):
        name = tables.LinkColumn('corporation_details', args=[A('name')])
        ticker = tables.Column()
        member_count = tables.Column(verbose_name='members')
        template_name = 'core/armada_table.html'
        class Meta:
            attrs = {'class': 'table table-condensed table-bordered table-striped span12'}
            orderable = True
            order_by = ('-member_count', 'name')
    def get(self, request):
        corporations_table = self.CorporationTable(Corporation.objects.all())
        tables.RequestConfig(request).configure(corporations_table)
        return self.render_to_response({
            'corporation_table': corporations_table,
            })
    def post(self, request):
        try:
            search_terms = request.POST.get('search', '')
            corporation = Corporation.objects.get_corporation(search_terms)
        except Corporation.DoesNotExist:
            corporation = None
        similar_corporations = Corporation.objects.filter(name__icontains=search_terms).exclude(name=search_terms)
        print similar_corporations
        corporations_table = self.CorporationTable(Corporation.objects.all())
        tables.RequestConfig(request).configure(corporations_table)
        return self.render_to_response({
            'corporation_table': corporations_table,
            'corporation': corporation,
            'similar_corporations': similar_corporations,
            'search_terms': search_terms,
            })



