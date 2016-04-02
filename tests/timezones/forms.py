from django import forms

from .models import Event


class EventForm(forms.Form):
    dt = forms.DateTimeField()


class EventSplitForm(forms.Form):
    dt = forms.SplitDateTimeField()


class EventLocalizedForm(forms.Form):
    use_required_attribute = True  # RemovedInDjango20Warning
    dt = forms.DateTimeField(localize=True)


class EventModelForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'


class EventLocalizedModelForm(forms.ModelForm):
    use_required_attribute = True  # RemovedInDjango20Warning

    class Meta:
        model = Event
        fields = '__all__'
        localized_fields = '__all__'
