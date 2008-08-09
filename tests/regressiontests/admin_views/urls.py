from django.conf.urls.defaults import *
from django.contrib import admin
import views

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/secure-view/$', views.secure_view),
    (r'^admin/(.*)', admin.site.root),
)
