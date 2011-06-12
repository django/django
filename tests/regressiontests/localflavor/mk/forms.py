from django.forms import ModelForm
from models import MKPerson

class MKPersonForm(ModelForm):

    class Meta:
        model = MKPerson
