from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
import django_tables2 as tables
from armada.eve.ccpmodels import MapSolarsystem
from armada.lib.evemodels import get_location_name

class SystemItemPriceColumn(tables.TemplateColumn):
    system = MapSolarsystem.objects.get(solarsystemname='Jita')
    template_code = ''
    def __init__(self, *args, **kwargs):
        template_code = '{% load eve_tags %}{% system_item_price '
        if 'system' in kwargs:
            template_code += str(kwargs['system'].pk)
        else:
            template_code += '%d ' % self.system.pk
        if 'record_accessor' in kwargs:
            template_code += 'record.%s %%}' % kwargs.pop('record_accessor')
        else:
            template_code += 'record %}'
        super(SystemItemPriceColumn, self).__init__(*args, template_code=template_code, **kwargs)

class PriceColumn(tables.Column):
    def render(self, value):
        return format(value, ',.2f')

class LocationColumn(tables.Column):
    def render(self, value):
        return get_location_name(value)

class ItemColumn(tables.Column):
    def render(self, value):
        return mark_safe('<a href="%s">%s</a>' % (reverse('item_details', args=(value,)), value))
