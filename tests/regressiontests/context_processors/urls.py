from django.conf.urls.defaults import *

import views


urlpatterns = patterns('',
    (r'^request_attrs/$', views.request_processor),
    (r'^auth_processor_no_attr_access/$', views.auth_processor_no_attr_access),
    (r'^auth_processor_attr_access/$', views.auth_processor_attr_access),
    (r'^auth_processor_user/$', views.auth_processor_user),
    (r'^auth_processor_perms/$', views.auth_processor_perms),
    (r'^auth_processor_messages/$', views.auth_processor_messages),
    url(r'^userpage/(.+)/$', views.userpage, name="userpage"),
)
