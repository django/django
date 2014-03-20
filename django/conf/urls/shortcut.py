import warnings

from django.conf.urls import patterns
from django.utils.deprecation import RemovedInDjango18Warning

warnings.warn("django.conf.urls.shortcut will be removed in Django 1.8.",
    RemovedInDjango18Warning)

urlpatterns = patterns('django.views',
    (r'^(?P<content_type_id>\d+)/(?P<object_id>.*)/$', 'defaults.shortcut'),
)
