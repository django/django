from django.conf.urls import include, url
from django.contrib import admin

from . import views

ns_patterns = ([
    url(r'^xview/func/$', views.xview_dec(views.xview), name='func'),
], 'test')

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admindocs/', include('django.contrib.admindocs.urls')),
    url(r'^', include(ns_patterns, namespace='test')),
    url(r'^xview/func/$', views.xview_dec(views.xview)),
    url(r'^xview/class/$', views.xview_dec(views.XViewClass.as_view())),
]
