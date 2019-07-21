from django.urls import path

from . import views

urlpatterns = [
    path('render/', views.render_view),
    path('render/multiple_templates/', views.render_view_with_multiple_templates),
    path('render/content_type/', views.render_view_with_content_type),
    path('render/status/', views.render_view_with_status),
    path('render/using/', views.render_view_with_using),
]
