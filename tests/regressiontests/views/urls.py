from os import path

from django.conf.urls.defaults import *

from models import *
import views

base_dir = path.dirname(path.abspath(__file__))
media_dir = path.join(base_dir, 'media')
locale_dir = path.join(base_dir, 'locale')

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views',),
}

date_based_info_dict = { 
    'queryset': Article.objects.all(), 
    'date_field': 'date_created', 
    'month_format': '%m', 
} 

urlpatterns = patterns('',
    (r'^$', views.index_page),
    
    # Default views
    (r'^shortcut/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    (r'^non_existing_url/', 'django.views.defaults.page_not_found'),
    (r'^server_error/', 'django.views.defaults.server_error'),
    
    # i18n views
    (r'^i18n/', include('django.conf.urls.i18n')),    
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    
    # Static views
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_dir}),
    
	# Date-based generic views
    (r'^date_based/object_detail/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$', 
        'django.views.generic.date_based.object_detail', 
        dict(slug_field='slug', **date_based_info_dict)), 
    (r'^date_based/object_detail/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/allow_future/$', 
        'django.views.generic.date_based.object_detail', 
        dict(allow_future=True, slug_field='slug', **date_based_info_dict)), 
    (r'^date_based/archive_month/(?P<year>\d{4})/(?P<month>\d{1,2})/$', 
        'django.views.generic.date_based.archive_month', 
        date_based_info_dict),     
)
