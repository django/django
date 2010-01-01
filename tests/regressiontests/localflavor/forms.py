from django.forms import ModelForm
from models import Place

class PlaceForm(ModelForm):
    """docstring for PlaceForm"""
    class Meta:
        model = Place
