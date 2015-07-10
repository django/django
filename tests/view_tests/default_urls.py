from django.conf.urls import url
from django.contrib import admin

urlpatterns = [
    # This is the same as in the default project template
    url(r'^admin/', admin.site.urls),
]
