from django import forms

from .models import Event

class EventForm(forms.Form):
    dt = forms.DateTimeField()

class EventSplitForm(forms.Form):
    dt = forms.SplitDateTimeField()

class EventModelForm(forms.ModelForm):
    class Meta:
        model = Event
