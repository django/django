from django.conf.urls import include, url
from django.views import View


def view1(request):
    pass


def view2(request):
    pass


class View3(View):
    pass


nested = ([
    url(r'^view1/$', view1, name='view1'),
    url(r'^view3/$', View3.as_view(), name='view3'),
], 'backend')

urlpatterns = [
    url(r'^some/path/', include(nested, namespace='nested')),
    url(r'^view2/$', view2, name='view2'),
]
