from django.forms import ModelForm
from models import USPlace

class USPlaceForm(ModelForm):

    class Meta:
        model = USPlace
