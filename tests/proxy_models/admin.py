from freedom.contrib import admin

from .models import TrackerUser, ProxyTrackerUser

admin.site.register(TrackerUser)
admin.site.register(ProxyTrackerUser)
