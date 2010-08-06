from django.forms import ModelForm
from models import USPlace

class USPlaceForm(ModelForm):
    """docstring for PlaceForm"""
    class Meta:
        model = USPlace
