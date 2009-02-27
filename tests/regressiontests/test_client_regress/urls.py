from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
import views

urlpatterns = patterns('',
    (r'^no_template_view/$', views.no_template_view),
    (r'^staff_only/$', views.staff_only_view),
    (r'^get_view/$', views.get_view),
    (r'^request_data/$', views.request_data),
    url(r'^arg_view/(?P<name>.+)/$', views.view_with_argument, name='arg_view'),
    (r'^login_protected_redirect_view/$', views.login_protected_redirect_view),
    (r'^redirects/$', redirect_to, {'url': '/test_client_regress/redirects/further/'}),
    (r'^redirects/further/$', redirect_to, {'url': '/test_client_regress/redirects/further/more/'}),
    (r'^redirects/further/more/$', redirect_to, {'url': '/test_client_regress/no_template_view/'}),
    (r'^redirect_to_non_existent_view/$', redirect_to, {'url': '/test_client_regress/non_existent_view/'}),
    (r'^redirect_to_non_existent_view2/$', redirect_to, {'url': '/test_client_regress/redirect_to_non_existent_view/'}),
    (r'^redirect_to_self/$', redirect_to, {'url': '/test_client_regress/redirect_to_self/'}),
    (r'^circular_redirect_1/$', redirect_to, {'url': '/test_client_regress/circular_redirect_2/'}),
    (r'^circular_redirect_2/$', redirect_to, {'url': '/test_client_regress/circular_redirect_3/'}),
    (r'^circular_redirect_3/$', redirect_to, {'url': '/test_client_regress/circular_redirect_1/'}),
    (r'^set_session/$', views.set_session_view),
    (r'^check_session/$', views.check_session_view),
    (r'^request_methods/$', views.request_methods_view),
)
