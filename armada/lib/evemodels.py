from armada.eve.ccpmodels import MapDenormalize
from armada.eve.models import ConquerableStation

def get_attributes_by_categories(item):
    type_attributes = DgmTypeattribute.objects.filter(type=item)
    attribute_types = item.attribute
    attribute_categories = DgmAttributecategory.objects.filter(pk__in=attribute_types)
    return (type_attributes, attribute_types, attribute_categories)

def get_location_name(locationid):
    try:
        loc = MapDenormalize.objects.get(pk=locationid)
        return loc.itemname
    except MapDenormalize.DoesNotExist:
        pass
    try:
        loc = ConquerableStation.objects.get(pk=locationid)
        return loc.name
    except ConquerableStation.DoesNotExist:
        pass
    return locationid
