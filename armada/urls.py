from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from core.views import ArmadaView

urlpatterns = patterns('',
    url(r'^$', ArmadaView.as_view(), name='home'),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^core/', include('armada.core.urls')),
    url(r'^eve/', include('armada.eve.urls')),
    url(r'^capsuler/', include('armada.capsuler.urls')),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
