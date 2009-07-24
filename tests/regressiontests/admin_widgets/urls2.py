
from django.conf.urls.defaults import *
import widgetadmin

urlpatterns = patterns('',
    (r'^deep/down/admin/(.*)', widgetadmin.site.root),
)
