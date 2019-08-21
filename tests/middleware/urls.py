from django.urls import path, re_path

from . import views

urlpatterns = [
    path('noslash', views.empty_view),
    path('slash/', views.empty_view),
    path('needsquoting#/', views.empty_view),
    # Accepts paths with two leading slashes.
    re_path(r'^(.+)/security/$', views.empty_view),
]
