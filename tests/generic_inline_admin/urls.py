from django.conf.urls import url

from . import admin

urlpatterns = [
    url(r'^generic_inline_admin/admin/', admin.site.urls),
]
