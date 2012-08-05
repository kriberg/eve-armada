from django.http import HttpResponseForbidden
from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.template import Context
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin

from templatetags.viewlets import *
import dispatcher

class Viewlet(TemplateResponseMixin, View):
    template_name = None
    task_name = None
    url_pattern = None
    url = None
    taskid = None
    def hook(self, template_name, task_name, url, url_pattern, login_required=True):
        self.template_name = template_name
        self.task_name = task_name
        self.url = url
        self.url_pattern = url_pattern
        self.login_required = login_required
    def enqueue(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        taskid = dispatcher.dispatch(request.session, self.task_name, context, *args, **kwargs)
        return self
    def get(self, request, taskid):
        print 'viewlet get triggered'
        viewlet_descriptor = request.session.get(taskid)
        if not viewlet_descriptor:
            return HttpResponseForbidden()

        result = viewlet_descriptor['result']
        result.get()
        self.template_name = viewlet_descriptor['template_name']
        return self.render_to_response(viewlet_descriptor['context'])
    def render(self):
        print 'viewlet render triggered'
        resp = self.response_class(self.request,
                self.template_name,
                Context(self.context))
        template = resp.resolve_template(self.template_name)
        context = resp.resolve_context(self.context)
        content = template.render(context)
        return content
    def get_url(self):
        if not self.url.endswith('/'):
            return '%s/%s/' % (self.url, self.taskid)
        else:
            return '%s%s/' % (self.url, self.taskid)


class TaskViewletsView(TemplateResponseMixin, View):
    __viewlets = {}
    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)
        super(TemplateResponseMixin, self).__init__(*args, **kwargs)
        self.viewlets()

    def viewlets(self):
        raise NotImplemented()

    def add_viewlet(self, name, viewlet):
        self.__viewlets[name] = viewlet

    def get_viewlet(self, name):
        return self.__viewlets[name]

    def viewlet_urls(self):
        urls = []
        for viewlet_name in self.__viewlets:
            viewlet = self.__viewlets[viewlet_name]
            if viewlet.url_pattern:
                if viewlet.login_required:
                    view = login_required(Viewlet.as_view())
                else:
                    view = Viewlet.as_view()
                urls.append(url(viewlet.url_pattern, view))
        return urls




