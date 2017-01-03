from django.conf.urls import url


class ViewContainer(object):
    def method_view(self, request):
        pass

    @classmethod
    def classmethod_view(cls, request):
        pass


view_container = ViewContainer()


urlpatterns = [
    url(r'^$', view_container.method_view, name='instance-method-url'),
    url(r'^$', ViewContainer.classmethod_view, name='instance-method-url'),
]
