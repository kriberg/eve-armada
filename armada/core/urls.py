from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from armada.core.views import PriceView, \
        SystemPriceView


urlpatterns = patterns('',
        url(r'^data/prices/$', PriceView.as_view()),
        url(r'^data/prices/(?P<systemid>\d+)/$', SystemPriceView.as_view()),
        )

