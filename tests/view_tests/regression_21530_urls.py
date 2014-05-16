from django.conf.urls import url

urlpatterns = [
    url(r'^index/$', 'view_tests.views.index_page', name='index'),
]
