from django.conf.urls import url

from .admin import site

urlpatterns = [
    url(r'^admin/', site.urls),
]
