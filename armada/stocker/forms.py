from django.forms import *

from armada.stocker.models import *
from armada.lib.evemodels import get_location_id

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
        exclude = ('team', 'settings')


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
