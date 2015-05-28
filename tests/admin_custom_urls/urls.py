from django.conf.urls import url

from .models import site

urlpatterns = [
    url(r'^admin/', site.urls),
]
