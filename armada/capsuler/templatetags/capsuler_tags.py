from django import template
register = template.Library()

from armada.capsuler.models import UserPilot
from armada.eve.models import InvType

@register.simple_tag()
def pilot_property(pilot, key):
    value = pilot.get_property(key)
    if key == 'balance':
        return "{:,}".format(float(value))
    elif key == 'cloneSkillPoints':
        return "{:,}".format(int(value))
    else:
        return value

@register.simple_tag()
def skill_level_image(level):
    return '<img src="/static/core/img/skill-level%d.png"\
            alt="skill level %d" />' % (level, level)

@register.simple_tag()
def skill_indicator_image(level):
    if level == 5:
        return '<img src="/static/core/img/desc-skill-complete.png" width="24"\
                height="24" alt="completed skill" />'
    else:
        return '<img src="/static/core/img/desc-skill-normal.png" width="24"\
                height="24" alt="normal skill" />'

@register.simple_tag()
def skill_in_training(pilot):
    LEVELS = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}
    s = pilot.get_skill_in_training()

    if not s.skillInTraining:
        return '<span class="label">No skill in training!</span>'
    else:
        id = 'skill-%d' % pilot.pk
        skill = InvType.objects.get(pk=s.trainingTypeID)
        return '%s %s, <span id="%s"></span>\
                <script type="text/javascript">tq_countdown(%d, "%s");</script>' % (skill,
                        LEVELS[s.trainingToLevel], id, s.trainingEndTime, id)

