from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    (r'^no_template_view/$', views.no_template_view),
    (r'^staff_only/$', views.staff_only_view),
    (r'^get_view/$', views.get_view),
    (r'^request_data/$', views.request_data),
    url(r'^arg_view/(?P<name>.+)/$', views.view_with_argument, name='arg_view'),
    (r'^login_protected_redirect_view/$', views.login_protected_redirect_view),
    (r'^set_session/$', views.set_session_view),
    (r'^check_session/$', views.check_session_view),
    (r'^request_methods/$', views.request_methods_view),
)
