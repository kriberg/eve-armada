from django import template
register = template.Library()

from capsuler.models import UserPilot

@register.simple_tag()
def pilot_property(pilot, key):
    return pilot.get_property(key)

@register.simple_tag()
def skill_level_image(level):
    return '<img src="/static/core/img/desc-browser-level%d.png" alt="skill level %d" />' % (level, level)

@register.simple_tag()
def skill_indicator_image(level):
    if level == 5:
        return '<img src="/static/core/img/desc-skill-complete.png" width="24" height="24" alt="completed skill" />'
    else:
        return '<img src="/static/core/img/desc-skill-normal.png" width="24" height="24" alt="normal skill" />'
