from django.forms import ModelForm
from models import AustralianPlace

class AustralianPlaceForm(ModelForm):
    """ Form for storing an Australian place. """
    class Meta:
        model = AustralianPlace
