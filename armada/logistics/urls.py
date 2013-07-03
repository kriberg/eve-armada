from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required

from armada.logistics.views import Logistics, \
        LogisticsTeamCreate, \
        LogisticsTeamDelete,\
        LogisticsTeamMembers, \
        LogisticsTeamDetails, \
        LogisticsTeamMemberAccept, \
        LogisticsTeamMemberDecline

urlpatterns = patterns('armada.logistics',
    url(r'^(?P<corporation_name>.+)/create/$', login_required(LogisticsTeamCreate.as_view()), name='logisticsteam_create'),
    url(r'^(?P<corporation_name>.+)/delete/(?P<team_name>.+)/$', login_required(LogisticsTeamDelete.as_view()), name='logisticsteam_delete'),
    url(r'^(?P<corporation_name>.+)/details/(?P<team_name>.+)/$', login_required(LogisticsTeamDetails.as_view()), name='logisticsteam_details'),
    url(r'^(?P<corporation_name>.+)/members/(?P<team_name>.+)/$', login_required(LogisticsTeamMembers.as_view()), name='logisticsteam_members'),
    url(r'^(?P<corporation_name>.+)/membership/(?P<membership_id>\d+)/accept/$', login_required(LogisticsTeamMemberAccept.as_view()), name='logisticsteammember_accept'),
    url(r'^(?P<corporation_name>.+)/membership/(?P<membership_id>\d+)/decline/$', login_required(LogisticsTeamMemberDecline.as_view()), name='logisticsteammember_decline'),
    url(r'^(?P<corporation_name>.+)/$', login_required(Logistics.as_view()), name='logistics_index'),
    )
