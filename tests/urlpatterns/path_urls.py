from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path('articles/2003/', views.empty_view, name='articles-2003'),
    path('articles/<int:year>/', views.empty_view, name='articles-year'),
    path('articles/<int:year>/<int:month>/', views.empty_view, name='articles-year-month'),
    path('articles/<int:year>/<int:month>/<int:day>/', views.empty_view, name='articles-year-month-day'),
    path('users/', views.empty_view, name='users'),
    path('users/<id>/', views.empty_view, name='user-with-id'),
    path('included_urls/', include('urlpatterns.included_urls')),
    re_path(r'^regex/(?P<pk>[0-9]+)/$', views.empty_view, name='regex'),
    re_path(r'^regex_optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?', views.empty_view, name='regex_optional'),
    path('', include('urlpatterns.more_urls')),
    path('<lang>/<path:url>/', views.empty_view, name='lang-and-path'),
]
