import django_tables2 as tables
from eve.ccpmodels import MapSolarsystem

class SystemItemPriceColumn(tables.TemplateColumn):
    system = MapSolarsystem.objects.get(solarsystemname='Jita')
    template_code = '{% load eve_tags %}{% system_item_price 30000142 record %}'
    def __init__(self, *args, **kwargs):
        super(SystemItemPriceColumn, self).__init__(*args, template_code=self.template_code, **kwargs)
        if 'system' in kwargs:
            self.system = system
        self.template_code = '{% load eve_tags %}{% system_item_price ' + str(self.system.pk) + ' record %}'

class PriceColumn(tables.TemplateColumn):
    def render(self, value):
        return format(value, ',.2f').replace(',', ' ')
