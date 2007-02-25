from django.conf import settings
from django.conf.urls.defaults import *

if settings.USE_I18N:
    i18n_view = 'django.views.i18n.javascript_catalog'
else:
    i18n_view = 'django.views.i18n.null_javascript_catalog'

urlpatterns = patterns('',
    ('^$', 'django.contrib.admin.views.main.index'),
    ('^r/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    ('^jsi18n/$', i18n_view, {'packages': 'django.conf'}),
    ('^logout/$', 'django.contrib.auth.views.logout'),
    ('^password_change/$', 'django.contrib.auth.views.password_change'),
    ('^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    ('^template_validator/$', 'django.contrib.admin.views.template.template_validator'),

    # "Add user" -- a special-case view
    ('^auth/user/add/$', 'django.contrib.admin.views.auth.user_add_stage'),
    # "Change user password" -- another special-case view
    ('^auth/user/(\d+)/password/$', 'django.contrib.admin.views.auth.user_change_password'),

    # Model-specific admin pages.
    ('^([^/]+)/([^/]+)/(?:(.+)/)?$', 'django.contrib.admin.views.main.model_admin_view'),
)

del i18n_view
