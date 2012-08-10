from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required
from core.views import PriceView, \
        SystemPriceView, \
        ArmadaView, \
        PilotListSubview


urlpatterns = patterns('',
        url(r'^data/prices/$', PriceView.as_view()),
        url(r'^data/prices/(?P<systemid>\d+)/$', SystemPriceView.as_view()),
        url(r'^tasks/pilotlist/(?P<taskid>.+)/$', PilotListSubview.as_view()),
        )

