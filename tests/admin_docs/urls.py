from django.conf.urls import include, patterns
from django.contrib import admin

from . import views

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^admindocs/', include('django.contrib.admindocs.urls')),
    (r'^xview/func/$', views.xview_dec(views.xview)),
    (r'^xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
