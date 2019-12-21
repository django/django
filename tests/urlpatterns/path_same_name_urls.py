from django.urls import path, re_path

from . import views

urlpatterns = [
    # Different number of arguments.
    path('number_of_args/0/', views.empty_view, name='number_of_args'),
    path('number_of_args/1/<value>/', views.empty_view, name='number_of_args'),
    # Different names of the keyword arguments.
    path('kwargs_names/a/<a>/', views.empty_view, name='kwargs_names'),
    path('kwargs_names/b/<b>/', views.empty_view, name='kwargs_names'),
    # Different path converters.
    path('converter/path/<path:value>/', views.empty_view, name='converter'),
    path('converter/str/<str:value>/', views.empty_view, name='converter'),
    path('converter/slug/<slug:value>/', views.empty_view, name='converter'),
    path('converter/int/<int:value>/', views.empty_view, name='converter'),
    path('converter/uuid/<uuid:value>/', views.empty_view, name='converter'),
    # Different regular expressions.
    re_path(r'^regex/uppercase/([A-Z]+)/', views.empty_view, name='regex'),
    re_path(r'^regex/lowercase/([a-z]+)/', views.empty_view, name='regex'),
]
