from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^render_to_response/$', views.render_to_response_view),
    url(r'^render_to_response/multiple_templates/$', views.render_to_response_view_with_multiple_templates),
    url(r'^render_to_response/request_context/$', views.render_to_response_view_with_request_context),
    url(r'^render_to_response/content_type/$', views.render_to_response_view_with_content_type),
    url(r'^render_to_response/dirs/$', views.render_to_response_view_with_dirs),
    url(r'^render_to_response/status/$', views.render_to_response_view_with_status),
    url(r'^render_to_response/using/$', views.render_to_response_view_with_using),
    url(r'^render_to_response/context_instance_misuse/$', views.render_to_response_with_context_instance_misuse),
    url(r'^render/$', views.render_view),
    url(r'^render/multiple_templates/$', views.render_view_with_multiple_templates),
    url(r'^render/base_context/$', views.render_view_with_base_context),
    url(r'^render/content_type/$', views.render_view_with_content_type),
    url(r'^render/dirs/$', views.render_with_dirs),
    url(r'^render/status/$', views.render_view_with_status),
    url(r'^render/using/$', views.render_view_with_using),
    url(r'^render/current_app/$', views.render_view_with_current_app),
    url(r'^render/current_app_conflict/$', views.render_view_with_current_app_conflict),
]
