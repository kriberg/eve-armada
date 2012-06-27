from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required

from capsuler.views import APIView, \
        PilotListView, \
        PilotActivateView, \
        PilotDeactivateView, \
        PilotDetailsView


urlpatterns = patterns('',
        url(r'^api/$', login_required(APIView.as_view()), name='capsuler_api'),
        url(r'^pilots/$', login_required(PilotListView.as_view()), name='capsuler_pilots'),
        url(r'^pilots/activate/(?P<characterid>\d+)$', login_required(PilotActivateView.as_view()), name='capsuler_activate_pilot'),
        url(r'^pilots/deactivate/(?P<characterid>\d+)$', login_required(PilotDeactivateView.as_view()), name='capsuler_deactivate_pilot'),
        url(r'^pilots/(?P<name>.+)/$', login_required(PilotDetailsView.as_view()), name='capsuler_pilot_details'),
        url(r'^tasks/pilottabs/(?P<pilotid>\d+)/(?P<taskid>.+)/$', login_required(PilotDetailsView.TabView.as_view())),
        )
