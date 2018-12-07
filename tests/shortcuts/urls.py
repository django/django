from django.urls import path

from . import views

urlpatterns = [
    path('render_to_response/', views.render_to_response_view),
    path('render_to_response/multiple_templates/', views.render_to_response_view_with_multiple_templates),
    path('render_to_response/content_type/', views.render_to_response_view_with_content_type),
    path('render_to_response/status/', views.render_to_response_view_with_status),
    path('render_to_response/using/', views.render_to_response_view_with_using),
    path('render/', views.render_view),
    path('render/multiple_templates/', views.render_view_with_multiple_templates),
    path('render/content_type/', views.render_view_with_content_type),
    path('render/status/', views.render_view_with_status),
    path('render/using/', views.render_view_with_using),
]
