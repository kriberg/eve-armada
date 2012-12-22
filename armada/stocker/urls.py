from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required

from armada.stocker.views import Stocker, \
        StockTeamOverview, \
        StockTeamCreate, \
        StockTeamDelete, \
        StockTeamUpdate, \
        StockTeamDetails, \
        StockTeamMemberAccept, \
        StockTeamMemberDecline, \
        StockGroupView, \
        StockGroupViewItemsSubview, \
        StockGroupCreate, \
        StockGroupDelete, \
        StockGroupDetails



urlpatterns = patterns('armada.stocker',
        url(r'^$', login_required(Stocker.as_view()), name='stocker_index'),
        url(r'^create/$', login_required(StockTeamCreate.as_view()), name='stockteam_create'),
        url(r'^delete/(?P<stockteam_id>\d+)/$', login_required(StockTeamDelete.as_view()), name='stockteam_delete'),
        url(r'^update/(?P<stockteam_id>\d+)/$', login_required(StockTeamUpdate.as_view()), name='stockteam_update'),
        url(r'^details/(?P<corporation_name>.+)/(?P<team_name>.+)/$', login_required(StockTeamDetails.as_view()), name='stockteam_details'),
        url(r'^membership/(?P<membership_id>\d+)/accept/$', login_required(StockTeamMemberAccept.as_view()), name='stockteammember_accept'),
        url(r'^membership/(?P<membership_id>\d+)/decline/$', login_required(StockTeamMemberDecline.as_view()), name='stockteammember_decline'),
        url(r'^view/(?P<corporation_name>.+)/(?P<team_name>.+)/create/$', login_required(StockGroupCreate.as_view()), name='stockgroup_create'),
        url(r'^view/(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/details/$', login_required(StockGroupDetails.as_view()), name='stockgroup_details'),
        url(r'^view/(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/delete/$', login_required(StockGroupDelete.as_view()), name='stockgroup_delete'),
        url(r'^view/(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/$', login_required(StockGroupView.as_view()), name='stockgroup_view'),
        url(r'^view/(?P<corporation_name>.+)/(?P<team_name>.+)/$', login_required(StockTeamOverview.as_view()), name='stockteam_overview'),
        url(r'^tasks/itemdata/(?P<taskid>.+)/$', login_required(StockGroupViewItemsSubview.as_view())),
        )

