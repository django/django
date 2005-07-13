from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^/?$', 'registration.passwords.password_reset', {'is_admin_site' : True}),
    (r'^done/$', 'registration.passwords.password_reset_done'),
)
