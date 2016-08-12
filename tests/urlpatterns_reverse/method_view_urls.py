from django.conf.urls import url
from django.http import HttpResponse


class ViewContainer(object):
    def method_view(self, request):
        return HttpResponse('')

    @classmethod
    def classmethod_view(cls, request):
        return HttpResponse('')

view_container = ViewContainer()


urlpatterns = [
    url(r'^$', view_container.method_view, name='instance-method-url'),
    url(r'^$', ViewContainer.classmethod_view, name='instance-method-url'),
]
