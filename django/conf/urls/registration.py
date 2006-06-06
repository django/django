from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout'),
    (r'^login_another/$', 'django.contrib.auth.views.logout_then_login'),

    (r'^register/$', 'ellington.registration.views.registration.signup'),
    (r'^register/(?P<challenge_string>\w{32})/$', 'ellington.registration.views.registration.register_form'),

    (r'^profile/$', 'ellington.registration.views.profile.profile'),
    (r'^profile/welcome/$', 'ellington.registration.views.profile.profile_welcome'),
    (r'^profile/edit/$', 'ellington.registration.views.profile.edit_profile'),

    (r'^password_reset/$', 'django.contrib.auth.views.password_reset'),
    (r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^password_change/$', 'django.contrib.auth.views.password_change'),
    (r'^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
)
