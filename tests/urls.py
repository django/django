from django.conf.urls import patterns, include

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

    # admin widget tests
    (r'widget_admin/', include('regressiontests.admin_widgets.urls')),

    # admin custom URL tests
    (r'^custom_urls/', include('regressiontests.admin_custom_urls.urls')),

    # admin scripts tests
    (r'^admin_scripts/', include('regressiontests.admin_scripts.urls')),

)
