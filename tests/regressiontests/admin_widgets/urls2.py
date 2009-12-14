
from django.conf.urls.defaults import *
import widgetadmin

urlpatterns = patterns('',
    (r'^deep/down/admin/', include(widgetadmin.site.urls)),
)
