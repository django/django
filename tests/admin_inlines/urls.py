from django.conf.urls import url

from . import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
]
