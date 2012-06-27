from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required
from core.views import PriceView, \
        SystemPriceView, \
        ArmadaView


urlpatterns = patterns('',
        url(r'^pilotlist/(?P<taskid>.+)/$', login_required(ArmadaView.PilotListView.as_view())),
        url(r'^data/prices/$', PriceView.as_view()),
        url(r'^data/prices/(?P<systemid>\d+)/$', SystemPriceView.as_view()),
        )
