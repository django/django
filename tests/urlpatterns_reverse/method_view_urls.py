from django.urls import path


class ViewContainer:
    def method_view(self, request):
        pass

    @classmethod
    def classmethod_view(cls, request):
        pass


view_container = ViewContainer()


urlpatterns = [
    path('', view_container.method_view, name='instance-method-url'),
    path('', ViewContainer.classmethod_view, name='instance-method-url'),
]
