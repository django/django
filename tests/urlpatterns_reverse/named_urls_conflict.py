from django.conf.urls import url

from .views import empty_view

urlpatterns = [
    # No kwargs
    url(r'^conflict/cannot-go-here/$', empty_view, name='name-conflict'),
    url(r'^conflict/$', empty_view, name='name-conflict'),
    # One kwarg
    url(r'^conflict-first/(?P<first>\w+)/$', empty_view, name='name-conflict'),
    url(r'^conflict-cannot-go-here/(?P<middle>\w+)/$', empty_view, name='name-conflict'),
    url(r'^conflict-middle/(?P<middle>\w+)/$', empty_view, name='name-conflict'),
    url(r'^conflict-last/(?P<last>\w+)/$', empty_view, name='name-conflict'),
    # Two kwargs
    url(r'^conflict/(?P<another>\w+)/(?P<extra>\w+)/cannot-go-here/$', empty_view, name='name-conflict'),
    url(r'^conflict/(?P<extra>\w+)/(?P<another>\w+)/$', empty_view, name='name-conflict'),
]
