from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.forms.models import modelformset_factory

from celery.execute import send_task
from datetime import datetime
import django_tables2 as tables
from django_tables2.utils import A
from armada.lib.columns import SystemItemPriceColumn, \
        LocationColumn, \
        ItemColumn
from armada.tasks.dispatcher import *
from armada.tasks.views import *
from armada.corporation.models import *

