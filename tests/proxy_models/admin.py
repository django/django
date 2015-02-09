from django.contrib import admin

from .models import ProxyTrackerUser, TrackerUser

admin.site.register(TrackerUser)
admin.site.register(ProxyTrackerUser)
