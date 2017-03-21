from django.conf.urls import url

from .admin import site

urlpatterns = [
    url(r'^test_admin/admin/', site.urls),
]
