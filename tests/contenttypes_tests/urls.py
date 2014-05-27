from __future__ import unicode_literals

from freedom.conf.urls import url
from freedom.contrib.contenttypes import views

urlpatterns = [
    url(r'^shortcut/([0-9]+)/(.*)/$', views.shortcut),
]
