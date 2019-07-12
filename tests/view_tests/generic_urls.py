from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views
from .models import Article, DateArticle

date_based_info_dict = {
    'queryset': Article.objects.all(),
    'date_field': 'date_created',
    'month_format': '%m',
}

object_list_dict = {
    'queryset': Article.objects.all(),
    'paginate_by': 2,
}

object_list_no_paginate_by = {
    'queryset': Article.objects.all(),
}

numeric_days_info_dict = dict(date_based_info_dict, day_format='%d')

date_based_datefield_info_dict = dict(date_based_info_dict, queryset=DateArticle.objects.all())

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html')),
    path('accounts/logout/', auth_views.LogoutView.as_view()),

    # Special URLs for particular regression cases.
    path('中文/target/', views.index_page),
]

# redirects, both temporary and permanent, with non-ASCII targets
urlpatterns += [
    path('nonascii_redirect/', RedirectView.as_view(url='/中文/target/', permanent=False)),
    path('permanent_nonascii_redirect/', RedirectView.as_view(url='/中文/target/', permanent=True)),
]

# json response
urlpatterns += [
    path('json/response/', views.json_response_view),
]
