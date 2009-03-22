from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # test_client modeltest urls
    (r'^test_client/', include('modeltests.test_client.urls')),
    (r'^test_client_regress/', include('regressiontests.test_client_regress.urls')),

    # File upload test views
    (r'^file_uploads/', include('regressiontests.file_uploads.urls')),

    # Always provide the auth system login and logout views
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),

    # test urlconf for {% url %} template tag
    (r'^url_tag/', include('regressiontests.templates.urls')),

    # django built-in views
    (r'^views/', include('regressiontests.views.urls')),

    # test urlconf for middleware tests
    (r'^middleware/', include('regressiontests.middleware.urls')),

    # admin view tests
    (r'^test_admin/', include('regressiontests.admin_views.urls')),
    (r'^generic_inline_admin/', include('regressiontests.generic_inline_admin.urls')),

    # admin widget tests
    (r'widget_admin/', include('regressiontests.admin_widgets.urls')),

    (r'^utils/', include('regressiontests.utils.urls')),

    # test urlconf for syndication tests
    (r'^syndication/', include('regressiontests.syndication.urls')),

    # conditional get views
    (r'condition/', include('regressiontests.conditional_processing.urls')),
)
