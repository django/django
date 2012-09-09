from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^', include('django.contrib.comments.urls')),

    # Provide the auth system login and logout views
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
)
