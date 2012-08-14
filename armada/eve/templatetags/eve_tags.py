from django import template
from armada.eve.models import TypeAttributesView, \
        Corporation, \
        Alliance, \
        Character

from BeautifulSoup import BeautifulSoup
import json
register = template.Library()

@register.simple_tag()
def invtype_icon(item, size):
    return '<img src="http://image.eveonline.com/Type/%d_%d.png" alt="%s" />' % (item.id, size, item.typename)

@register.simple_tag()
def invtype_render(item, size):
    return '<img src="http://image.eveonline.com/Render/%d_%d.png" alt="%s" />' % (item.id, size,  item.typename)

@register.simple_tag()
def system_item_price(systemid, item):
    return '<span name="%d:%d" class="system-item-price"><img style="text-align: center;" src="/static/core/img/spinner.gif" alt="spinner" /></span>' % (systemid, item.pk)

@register.filter
def evehtmlcleaner(value):
    bs = BeautifulSoup(value.replace('<br>', '\n').replace('<br />', '\n'))
    return bs.text

@register.simple_tag()
def character_portrait(character, size):
    return '<img src="http://image.eveonline.com/Character/%d_%d.jpg" alt="%s" />' % (character.pk, size, character.name)
