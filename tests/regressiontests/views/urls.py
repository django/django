from os import path

from django.conf.urls.defaults import *
import views

base_dir = path.dirname(path.abspath(__file__))
media_dir = path.join(base_dir, 'media')
locale_dir = path.join(base_dir, 'locale')

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views',),
}

urlpatterns = patterns('',
    (r'^$', views.index_page),
    (r'^shortcut/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    (r'^non_existing_url/', 'django.views.defaults.page_not_found'),
    (r'^server_error/', 'django.views.defaults.server_error'),
    
    (r'^i18n/', include('django.conf.urls.i18n')),    
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    (r'^jsi18n_test/$', views.jsi18n_test),
    
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_dir}),
)
