from django.conf.urls import url

from . import widgetadmin

urlpatterns = [
    url(r'^', widgetadmin.site.urls),
]
