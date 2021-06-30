from mango.contrib.contenttypes import views
from mango.urls import re_path

urlpatterns = [
    re_path(r'^shortcut/([0-9]+)/(.*)/$', views.shortcut),
]
