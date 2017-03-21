from django.conf.urls import include, url
from django.contrib import admin

from . import views

backend_urls = ([
    url(r'^something/$', views.XViewClass.as_view(), name='something'),
], 'backend')

urlpatterns = [
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^api/backend/', include(backend_urls, namespace='backend')),
]
