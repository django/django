from django.conf.urls.defaults import patterns
from django.contrib.auth.urls import urlpatterns

# special urls for auth test cases
urlpatterns += patterns('',
    (r'^logout/custom_query/$', 'django.contrib.auth.views.logout', dict(redirect_field_name='follow')),
    (r'^logout/next_page/$', 'django.contrib.auth.views.logout', dict(next_page='/somewhere/')),
)

