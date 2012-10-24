from django.conf.urls import patterns, include, url
from django.contrib.auth.urls import urlpatterns
from django.contrib import admin


admin.autodiscover()

urlpatterns = urlpatterns + patterns('',
    url(r'^admin/', include(admin.site.urls)),
)
