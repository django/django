from django.contrib import admin

from .models import Event, Timestamp


class EventAdmin(admin.ModelAdmin):
    list_display = ('dt',)


class TimestampAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'updated')

site = admin.AdminSite(name='admin_tz')
site.register(Event, EventAdmin)
site.register(Timestamp, TimestampAdmin)
