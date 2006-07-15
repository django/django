from django.conf.urls.defaults import *
from django.contrib.history.models import ChangeLog

info_dict = {
    'queryset': ChangeLog.objects.all(),
}

urlpatterns = patterns('',
    (r'^$', 'django.contrib.history.views.main.index'),
    (r'^list/$', 'django.contrib.history.views.main.list'),
    (r'^detail/(?P<change_id>\d+)/$', 'django.contrib.history.views.main.detail'),
    (r'^changes/(?P<parent_id>\d+)/$', 'django.contrib.history.views.main.changes'),
)
