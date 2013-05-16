from django.conf.urls import patterns, include

urlpatterns = patterns('',
    # test_client urls
    (r'^test_client/', include('test_client.urls')),
    (r'^test_client_regress/', include('test_client_regress.urls')),

    # File upload test views
    (r'^file_uploads/', include('file_uploads.urls')),

    # Always provide the auth system login and logout views
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),

    # test urlconf for {% url %} template tag
    (r'^url_tag/', include('template_tests.urls')),

    # django built-in views
    (r'^views/', include('view_tests.urls')),

    # test urlconf for middleware tests
    (r'^middleware/', include('middleware.urls')),

    # admin widget tests
    (r'widget_admin/', include('admin_widgets.urls')),

    # admin custom URL tests
    (r'^custom_urls/', include('admin_custom_urls.urls')),

    # admin scripts tests
    (r'^admin_scripts/', include('admin_scripts.urls')),

)
