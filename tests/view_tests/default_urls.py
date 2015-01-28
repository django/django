from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    # This is the same as in the default project template
    url(r'^admin/', include(admin.site.urls)),
]
