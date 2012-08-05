from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
import django_tables2 as tables
from eve.ccpmodels import MapSolarsystem
from lib.evemodels import get_location_name

class SystemItemPriceColumn(tables.TemplateColumn):
    system = MapSolarsystem.objects.get(solarsystemname='Jita')
    template_code = '{% load eve_tags %}{% system_item_price 30000142 record %}'
    accessor = 'pk'
    def __init__(self, *args, **kwargs):
        super(SystemItemPriceColumn, self).__init__(*args, template_code=self.template_code, **kwargs)
        if 'system' in kwargs:
            self.system = kwargs['system']
        if 'accessor' in kwargs:
            self.accessor = kwargs['accessor']
        self.template_code = '{% load eve_tags %}{% system_item_price ' + str(self.system.pk) + ' record.' + str(self.accessor) + ' %}'

class PriceColumn(tables.TemplateColumn):
    def render(self, value):
        return format(value, ',.2f').replace(',', ' ')

class LocationColumn(tables.TemplateColumn):
    def render(self, value):
        return get_location_name(value)

class ItemColumn(tables.TemplateColumn):
    def render(self, value):
        return mark_safe('<a href="%s">%s</a>' % (reverse('item_details', args=(value,)), value))
