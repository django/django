
from django.conf.urls.defaults import *
import widgetadmin

urlpatterns = patterns('',
    (r'^', include(widgetadmin.site.urls)),
)
