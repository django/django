from django.conf.urls import patterns

from . import views


urlpatterns = patterns('',
    (r'^test_utils/get_person/(\d+)/$', views.get_person),
    (r'^test_utils/no_template_used/$', views.no_template_used),
)
