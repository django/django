from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # test_client modeltest urls
    (r'^test_client/', include('modeltests.test_client.urls')),

    # Always provide the auth system login and logout views
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.login'),

    # test urlconf for {% url %} template tag
    (r'^url_tag/', include('regressiontests.templates.urls')),
)
