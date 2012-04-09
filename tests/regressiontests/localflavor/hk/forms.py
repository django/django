from __future__ import absolute_import

from django.forms import ModelForm

from .models import HKPlace


class HKPlaceForm(ModelForm):

    class Meta:
        model = HKPlace
