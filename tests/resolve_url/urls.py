from django.conf.urls import patterns


urlpatterns = patterns('',
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout')
)
