from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

site = admin.AdminSite(name='custom_user_admin')


class CustomUserAdmin(UserAdmin):
    def log_change(self, request, object, message):
        # LogEntry.user column doesn't get altered to expect a UUID, so set an
        # integer manually to avoid causing an error.
        request.user.pk = 1
        super(CustomUserAdmin, self).log_change(request, object, message)

site.register(get_user_model(), CustomUserAdmin)

urlpatterns = [
    url(r'^admin/', site.urls),
]
