from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^render_to_response/$', views.render_to_response_view),
    url(r'^render_to_response/multiple_templates/$', views.render_to_response_view_with_multiple_templates),
    url(r'^render_to_response/content_type/$', views.render_to_response_view_with_content_type),
    url(r'^render_to_response/status/$', views.render_to_response_view_with_status),
    url(r'^render_to_response/using/$', views.render_to_response_view_with_using),
    url(r'^render/$', views.render_view),
    url(r'^render/multiple_templates/$', views.render_view_with_multiple_templates),
    url(r'^render/content_type/$', views.render_view_with_content_type),
    url(r'^render/status/$', views.render_view_with_status),
    url(r'^render/using/$', views.render_view_with_using),
]
