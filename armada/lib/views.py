from djangbone.views import BackboneAPIView
from django.http import HttpResponseForbidden
import django_tables2 as tables
from django.utils.safestring import mark_safe

class JSONView(BackboneAPIView):
    read_only=False
    def filter(self, request):
        pass

    def dispatch(self, request, *args, **kwargs):
        if self.read_only and request.method in ['PUT', 'DELETE']:
            return HttpResponseForbidden()
        else:
            self.base_queryset = self.filter(request)
            return super(JSONView, self).dispatch(request, *args, **kwargs)
