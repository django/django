from django.conf.urls import patterns, url, include
from django.views.generic import RedirectView

from . import views


urlpatterns = patterns('',
    (r'', include('test_client.urls')),

    (r'^no_template_view/$', views.no_template_view),
    (r'^staff_only/$', views.staff_only_view),
    (r'^get_view/$', views.get_view),
    (r'^request_data/$', views.request_data),
    (r'^request_data_extended/$', views.request_data, {'template': 'extended.html', 'data': 'bacon'}),
    url(r'^arg_view/(?P<name>.+)/$', views.view_with_argument, name='arg_view'),
    url(r'^nested_view/$', views.nested_view, name='nested_view'),
    (r'^login_protected_redirect_view/$', views.login_protected_redirect_view),
    (r'^redirects/$', RedirectView.as_view(url='/redirects/further/')),
    (r'^redirects/further/$', RedirectView.as_view(url='/redirects/further/more/')),
    (r'^redirects/further/more/$', RedirectView.as_view(url='/no_template_view/')),
    (r'^redirect_to_non_existent_view/$', RedirectView.as_view(url='/non_existent_view/')),
    (r'^redirect_to_non_existent_view2/$', RedirectView.as_view(url='/redirect_to_non_existent_view/')),
    (r'^redirect_to_self/$', RedirectView.as_view(url='/redirect_to_self/')),
    (r'^circular_redirect_1/$', RedirectView.as_view(url='/circular_redirect_2/')),
    (r'^circular_redirect_2/$', RedirectView.as_view(url='/circular_redirect_3/')),
    (r'^circular_redirect_3/$', RedirectView.as_view(url='/circular_redirect_1/')),
    (r'^redirect_other_host/$', RedirectView.as_view(url='https://otherserver:8443/no_template_view/')),
    (r'^set_session/$', views.set_session_view),
    (r'^check_session/$', views.check_session_view),
    (r'^request_methods/$', views.request_methods_view),
    (r'^check_unicode/$', views.return_unicode),
    (r'^check_binary/$', views.return_undecodable_binary),
    (r'^parse_unicode_json/$', views.return_json_file),
    (r'^check_headers/$', views.check_headers),
    (r'^check_headers_redirect/$', RedirectView.as_view(url='/check_headers/')),
    (r'^body/$', views.body),
    (r'^read_all/$', views.read_all),
    (r'^read_buffer/$', views.read_buffer),
    (r'^request_context_view/$', views.request_context_view),
)
