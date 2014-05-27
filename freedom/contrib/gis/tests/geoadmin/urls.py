from freedom.conf.urls import include, url
from freedom.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
]
