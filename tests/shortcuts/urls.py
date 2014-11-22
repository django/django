from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^render_to_response/$', views.render_to_response_view),
    url(r'^render_to_response/request_context/$', views.render_to_response_view_with_request_context),
    url(r'^render_to_response/content_type/$', views.render_to_response_view_with_content_type),
    url(r'^render_to_response/dirs/$', views.render_to_response_view_with_dirs),
    url(r'^render/$', views.render_view),
    url(r'^render/base_context/$', views.render_view_with_base_context),
    url(r'^render/content_type/$', views.render_view_with_content_type),
    url(r'^render/dirs/$', views.render_with_dirs),
    url(r'^render/status/$', views.render_view_with_status),
    url(r'^render/current_app/$', views.render_view_with_current_app),
    url(r'^render/current_app_conflict/$', views.render_view_with_current_app_conflict),
]
