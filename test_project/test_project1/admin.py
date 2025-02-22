from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from .models import Event
from django.contrib.admin.widgets import AdminSplitDateTime
from django import forms

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'event_datetime' in self.fields:
            self.fields['event_datetime'].widget.attrs.update({
                'aria-label': 'Event Date & Time'
            })


class EventAdmin(admin.ModelAdmin):
    form = EventAdminForm

admin.site.register(Event, EventAdmin)

