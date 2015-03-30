from django.conf.urls import include, url

from .models import site

urlpatterns = [
    url(r'^admin/', include(site.urls)),
]
