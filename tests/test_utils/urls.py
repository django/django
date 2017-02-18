from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^test_utils/get_person/([0-9]+)/$', views.get_person),
    url(r'^test_utils/no_template_used/$', views.no_template_used),
]
