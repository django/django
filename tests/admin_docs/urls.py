from django.conf.urls import include, patterns, url
from django.contrib import admin

from . import views

ns_patterns = patterns('',
    url(r'^xview/func/$', views.xview_dec(views.xview), name='func'),
)

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^admindocs/', include('django.contrib.admindocs.urls')),
    (r'^', include(ns_patterns, namespace='test')),
    (r'^xview/func/$', views.xview_dec(views.xview)),
    (r'^xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
