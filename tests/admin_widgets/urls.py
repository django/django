from django.conf.urls import include, url

from . import widgetadmin

urlpatterns = [
    url(r'^', include(widgetadmin.site.urls)),
]
