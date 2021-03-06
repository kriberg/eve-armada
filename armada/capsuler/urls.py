from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required

from armada.capsuler.views import APIView, \
        PilotListView, \
        PilotActivateView, \
        PilotDeactivateView, \
        PilotDetailsView, \
        PilotAssetsView, \
        AssetsJSONView


urlpatterns = patterns('',
        url(r'^api/$', login_required(APIView.as_view()), name='capsuler_api'),
        url(r'^pilots/$', login_required(PilotListView.as_view()), name='capsuler_pilots'),
        url(r'^pilots/activate/(?P<characterid>\d+)$', login_required(PilotActivateView.as_view()), name='capsuler_activate_pilot'),
        url(r'^pilots/deactivate/(?P<characterid>\d+)$', login_required(PilotDeactivateView.as_view()), name='capsuler_deactivate_pilot'),
        url(r'^pilots/(?P<name>.+)/$', login_required(PilotDetailsView.as_view()), name='capsuler_pilot_details'),
        url(r'^assets/(?P<pilot_id>\d+)/data/$', login_required(AssetsJSONView.as_view())),
        url(r'^assets/(?P<name>.+)/$', login_required(PilotAssetsView.as_view()), name='capsuler_pilot_assets'),
        )

