from django.http import HttpResponseForbidden
from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.template import Context
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.utils.safestring import mark_safe

import dispatcher

class Subview(TemplateResponseMixin, View):
    template_name = None
    task_name = None
    sub_url = None

    def enqueue(self, request, *args, **kwargs):
        taskid = dispatcher.dispatch(request.session, self.task_name, *args, **kwargs)
        # If the taskid is None, then the task result is still cached and we
        # should render it diretcly. If not, task is queued and an ajax 
        # callback is added.
        if not taskid:
            content = self.render(request,
                    self.build_context(request, kwargs))
        else:
            if not self.sub_url.endswith('/'):
                task_url = '%s/%s/' % (self.sub_url, taskid)
            else:
                task_url = '%s%s/' % (self.sub_url, taskid)
            content = '''
            <div id="%s">
                <img src="/static/core/img/spinner.gif" alt="spinner" />
                <script type="text/javascript">
                    delayed_load("%s", "%s");
                </script>
            </div>
            ''' % (taskid, taskid, task_url)

        return mark_safe(content)

    def build_context(self, request, params):
        raise NotImplemented()

    def get(self, request, taskid):
        result = request.session.get(taskid)
        if not result:
            return HttpResponseForbidden()
        result['task'].get()
        context = self.build_context(request, result['params'])
        return self.render_to_response(context)

    def render(self, request, context):
        resp = self.response_class(request,
                self.template_name,
                Context(context))
        template = resp.resolve_template(self.template_name)
        context = resp.resolve_context(context)
        content = template.render(context)
        return content

