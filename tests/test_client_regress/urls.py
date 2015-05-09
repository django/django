from django.conf.urls import include, url
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    url(r'', include('test_client.urls')),

    url(r'^no_template_view/$', views.no_template_view),
    url(r'^staff_only/$', views.staff_only_view),
    url(r'^get_view/$', views.get_view),
    url(r'^request_data/$', views.request_data),
    url(r'^request_data_extended/$', views.request_data, {'template': 'extended.html', 'data': 'bacon'}),
    url(r'^arg_view/(?P<name>.+)/$', views.view_with_argument, name='arg_view'),
    url(r'^nested_view/$', views.nested_view, name='nested_view'),
    url(r'^login_protected_redirect_view/$', views.login_protected_redirect_view),
    url(r'^redirects/$', RedirectView.as_view(url='/redirects/further/')),
    url(r'^redirects/further/$', RedirectView.as_view(url='/redirects/further/more/')),
    url(r'^redirects/further/more/$', RedirectView.as_view(url='/no_template_view/')),
    url(r'^redirect_to_non_existent_view/$', RedirectView.as_view(url='/non_existent_view/')),
    url(r'^redirect_to_non_existent_view2/$', RedirectView.as_view(url='/redirect_to_non_existent_view/')),
    url(r'^redirect_to_self/$', RedirectView.as_view(url='/redirect_to_self/')),
    url(r'^redirect_to_self_with_changing_query_view/$', views.redirect_to_self_with_changing_query_view),
    url(r'^circular_redirect_1/$', RedirectView.as_view(url='/circular_redirect_2/')),
    url(r'^circular_redirect_2/$', RedirectView.as_view(url='/circular_redirect_3/')),
    url(r'^circular_redirect_3/$', RedirectView.as_view(url='/circular_redirect_1/')),
    url(r'^redirect_other_host/$', RedirectView.as_view(url='https://otherserver:8443/no_template_view/')),
    url(r'^set_session/$', views.set_session_view),
    url(r'^check_session/$', views.check_session_view),
    url(r'^request_methods/$', views.request_methods_view),
    url(r'^check_unicode/$', views.return_unicode),
    url(r'^check_binary/$', views.return_undecodable_binary),
    url(r'^json_response/$', views.return_json_response),
    url(r'^parse_unicode_json/$', views.return_json_file),
    url(r'^check_headers/$', views.check_headers),
    url(r'^check_headers_redirect/$', RedirectView.as_view(url='/check_headers/')),
    url(r'^body/$', views.body),
    url(r'^read_all/$', views.read_all),
    url(r'^read_buffer/$', views.read_buffer),
    url(r'^request_context_view/$', views.request_context_view),
    url(r'^render_template_multiple_times/$', views.render_template_multiple_times),
]
