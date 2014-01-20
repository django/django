from django.contrib import admin

from .models import Event, Timestamp


class EventAdmin(admin.ModelAdmin):
    list_display = ('dt',)

admin.site.register(Event, EventAdmin)


class TimestampAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'updated')

admin.site.register(Timestamp, TimestampAdmin)
