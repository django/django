from django.forms import CharField, Form, ModelForm
from .models import Dog


class PersonForm(Form):
    first_name = CharField()
    last_name = CharField()


class DogForm(ModelForm):
    class Meta:
        model = Dog
        fields = '__all__'
