from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django import forms
from .models import Event

class EventAdminForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'
        widgets = {
            'event_datetime': AdminSplitDateTime(),
        }
        labels = {
            'event_datetime': "Event Date & Time"
        }

class EventAdmin(admin.ModelAdmin):
    form = EventAdminForm

admin.site.register(Event, EventAdmin)
