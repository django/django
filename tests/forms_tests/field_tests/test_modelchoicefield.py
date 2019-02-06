from django.forms import ModelChoiceField, Form
from django.test import TestCase

from ..models import ChoiceOptionModel


class ModelChoiceFieldTest(TestCase):

    def test_disabled_field_1(self):

        opt1 = ChoiceOptionModel(12345)
        opt1.save()

        class MyForm(Form):
            field = ModelChoiceField(
                queryset=ChoiceOptionModel.objects.all(), disabled=True,
                initial=opt1)

        self.assertTrue(MyForm({}).is_valid())
