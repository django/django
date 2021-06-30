from mango.contrib import admin
from mango.urls import include, path

urlpatterns = [
    path('admin/', include(admin.site.urls)),
]
