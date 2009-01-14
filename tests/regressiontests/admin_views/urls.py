from django.conf.urls.defaults import *
from django.contrib import admin
import views
import customadmin

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/secure-view/$', views.secure_view),
    (r'^admin/', include(admin.site.urls)),
    (r'^admin2/', include(customadmin.site.urls)),
)
