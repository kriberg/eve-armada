from django.forms import *

from armada.stocker.models import *
from armada.lib.evemodels import get_location_id

class StockTeamForm(ModelForm):
    class Meta:
        model = StockTeam
        exclude = ('manager',)

class StockTeamUpdateForm(ModelForm):
    def clean_name(self):
        name = self.cleaned_data['name']
        instances = StockTeam.objects.filter(name=name,
                corporation=self.instance.corporation)
        if instances.count() > 0 and not self.instance in instances:
            raise ValidationError('Team %s for corporation %s already exists' % (name, self.instance.corporation))
        else:
            return name
    class Meta:
        model = StockTeam
        exclude = ('manager', 'corporation')

class StockGroupForm(ModelForm):
    def clean_location(self):
        name = self.cleaned_data['location']
        try:
            get_location_id(name)
            return name
        except:
            raise ValidationError('Location does not exist.')
    class Meta:
        model = StockGroup
        exclude = ('team',)

class StockGroupItemForm(ModelForm):
    item_name = CharField(widget=TextInput(attrs={'class': 'invtype'}))

    def clean_item_name(self):
        item_name = self.cleaned_data['item_name']
        try:
            return InvType.objects.get(typename=item_name).typename
        except:
            raise ValidationError('Item not found.')

    class Meta:
        model = StockGroupItem
        exclude = ('item',)
