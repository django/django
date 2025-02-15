from thibaud.contrib import admin
from thibaud.urls import path

urlpatterns = [
    # This is the same as in the default project template
    path("admin/", admin.site.urls),
]
