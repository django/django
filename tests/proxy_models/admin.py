from django.contrib import admin

from .models import ProxyTrackerUser, TrackerUser

site = admin.AdminSite(name='admin_proxy')
site.register(TrackerUser)
site.register(ProxyTrackerUser)
