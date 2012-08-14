from django.conf.urls.defaults import patterns, include, url
from armada.eve.views import ItemListView, \
        ItemView, \
        InvTypeJSON, \
        AllianceListView, \
        AllianceView, \
        CorporationView, \
        CorporationListView

urlpatterns = patterns('',
        url(r'^typeahead/invtype_name/', 'armada.eve.views.typeahead_invtype_name', name='eve_typeahead_invtype_name'),
        url(r'^data/invtype/$', InvTypeJSON.as_view()),
        url(r'^items/$', ItemListView.as_view(), name='item_list'),
        url(r'^items/(?P<name>.+)$', ItemView.as_view(), name='item_details'),
        url(r'^alliances/$', AllianceListView.as_view(), name='alliance_list'),
        url(r'^alliances/(?P<alliance>.+)$', AllianceView.as_view(), name='alliance_details'),
        url(r'^corporations/$', CorporationListView.as_view(), name='corporation_list'),
        url(r'^corporations/(?P<corporation>.+)$', CorporationView.as_view(), name='corporation_details'),
        )

