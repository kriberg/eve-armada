from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required

from armada.stocker.views import StockTeamOverview, \
        StockGroupView, \
        StockGroupViewItemsSubview, \
        StockGroupCreate, \
        StockGroupDelete, \
        StockGroupDetails



urlpatterns = patterns('armada.stocker',
        url(r'^tasks/itemdata/(?P<taskid>.+)/$',
            login_required(StockGroupViewItemsSubview.as_view())),
        url(r'^(?P<corporation_name>.+)/(?P<team_name>.+)/create/$',
            login_required(StockGroupCreate.as_view()),
            name='stockgroup_create'),
        url(r'^(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/details/$',
            login_required(StockGroupDetails.as_view()),
            name='stockgroup_details'),
        url(r'^(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/delete/$',
            login_required(StockGroupDelete.as_view()),
            name='stockgroup_delete'),
        url(r'^(?P<corporation_name>.+)/(?P<team_name>.+)/(?P<group_name>.+)/$',
            login_required(StockGroupView.as_view()),
            name='stockgroup_view'),
        url(r'^(?P<corporation_name>.+)/(?P<team_name>.+)/$',
            login_required(StockTeamOverview.as_view()),
            name='stockteam_overview'),
        )

