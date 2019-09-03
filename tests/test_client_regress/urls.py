from django.urls import include, path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', include('test_client.urls')),

    path('no_template_view/', views.no_template_view),
    path('staff_only/', views.staff_only_view),
    path('get_view/', views.get_view),
    path('request_data/', views.request_data),
    path('request_data_extended/', views.request_data, {'template': 'extended.html', 'data': 'bacon'}),
    path('arg_view/<name>/', views.view_with_argument, name='arg_view'),
    path('nested_view/', views.nested_view, name='nested_view'),
    path('login_protected_redirect_view/', views.login_protected_redirect_view),
    path('redirects/', RedirectView.as_view(url='/redirects/further/')),
    path('redirects/further/', RedirectView.as_view(url='/redirects/further/more/')),
    path('redirects/further/more/', RedirectView.as_view(url='/no_template_view/')),
    path('redirect_to_non_existent_view/', RedirectView.as_view(url='/non_existent_view/')),
    path('redirect_to_non_existent_view2/', RedirectView.as_view(url='/redirect_to_non_existent_view/')),
    path('redirect_to_self/', RedirectView.as_view(url='/redirect_to_self/')),
    path('redirect_to_self_with_changing_query_view/', views.redirect_to_self_with_changing_query_view),
    path('circular_redirect_1/', RedirectView.as_view(url='/circular_redirect_2/')),
    path('circular_redirect_2/', RedirectView.as_view(url='/circular_redirect_3/')),
    path('circular_redirect_3/', RedirectView.as_view(url='/circular_redirect_1/')),
    path('redirect_other_host/', RedirectView.as_view(url='https://otherserver:8443/no_template_view/')),
    path('set_session/', views.set_session_view),
    path('check_session/', views.check_session_view),
    path('request_methods/', views.request_methods_view),
    path('check_unicode/', views.return_unicode),
    path('check_binary/', views.return_undecodable_binary),
    path('json_response/', views.return_json_response),
    path('json_response_latin1/', views.return_json_response_latin1),
    path('parse_encoded_text/', views.return_text_file),
    path('check_headers/', views.check_headers),
    path('check_headers_redirect/', RedirectView.as_view(url='/check_headers/')),
    path('body/', views.body),
    path('read_all/', views.read_all),
    path('read_buffer/', views.read_buffer),
    path('request_context_view/', views.request_context_view),
    path('render_template_multiple_times/', views.render_template_multiple_times),
]
