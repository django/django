from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^login/$', 'django.views.auth.login.login'),
    (r'^logout/$', 'django.views.auth.login.logout'),
    (r'^login_another/$', 'django.views.auth.login.logout_then_login'),

    (r'^register/$', 'ellington.registration.views.registration.signup'),
    (r'^register/(?P<challenge_string>\w{32})/$', 'ellington.registration.views.registration.register_form'),

    (r'^profile/$', 'ellington.registration.views.profile.profile'),
    (r'^profile/welcome/$', 'ellington.registration.views.profile.profile_welcome'),
    (r'^profile/edit/$', 'ellington.registration.views.profile.edit_profile'),

    (r'^password_reset/$', 'django.views.registration.passwords.password_reset'),
    (r'^password_reset/done/$', 'django.views.registration.passwords.password_reset_done'),
    (r'^password_change/$', 'django.views.registration.passwords.password_change'),
    (r'^password_change/done/$', 'django.views.registration.passwords.password_change_done'),
)
