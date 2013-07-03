from django.forms import *

from armada.logistics.models import *

class LogisticsTeamForm(ModelForm):
    class Meta:
        model = LogisticsTeam
        exclude = ('corporation',)

class LogisticsTeamUpdateForm(ModelForm):
    def clean_name(self):
        name = self.cleaned_data['name']
        instances = LogisticsTeam.objects.filter(name=name,
            corporation=self.instance.corporation)
        if instances.count() > 0 and not self.instance in instances:
            raise ValidationError('Team %s for corporation %s already exists' % (name, self.instance.corporation))
        else:
            return name
    class Meta:
        model = LogisticsTeam
        exclude = ('corporation', 'team_type', 'creator')
