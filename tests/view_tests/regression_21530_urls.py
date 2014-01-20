from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^index/$', 'view_tests.views.index_page', name='index'),
)
