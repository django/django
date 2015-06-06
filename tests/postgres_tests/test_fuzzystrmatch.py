from django.contrib.postgres.functions import Levenshtein
from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import CharFieldModel, TextFieldModel


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class FuzzyStrMatchTest(PostgreSQLTestCase):
    Model = CharFieldModel

    @classmethod
    def setUpTestData(cls):
        cls.Model.objects.bulk_create([
            cls.Model(field="Emily"),
            cls.Model(field="Emelia"),
            cls.Model(field="Amelie"),
            cls.Model(field="Fred"),
        ])

    def test_soundex(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__soundex='Emelie'),
            ['Emily', 'Emelia'],
            transform=lambda instance: instance.field,
            ordered=False,
        )

    def test_metaphone(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__metaphone='Emelie'),
            ['Emily', 'Emelia'],
            transform=lambda instance: instance.field,
            ordered=False,
        )

    def test_double_metaphone(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__double_metaphone='Emelie'),
            ['Emily', 'Emelia', 'Amelie'],
            transform=lambda instance: instance.field,
            ordered=False,
        )

    def test_levenshtein(self):
        self.assertQuerysetEqual(
            self.Model.objects.annotate(
                distance=Levenshtein('field', 'Emelie')).order_by('distance'),
            [('Emelia', 1), ('Amelie', 1), ('Emily', 3), ('Fred', 5)],
            transform=lambda instance: (instance.field, instance.distance),
            ordered=True
        )


class FuzzyStrMatchTextFieldTest(FuzzyStrMatchTest):
    """
    TextField should have the exact same behavior as CharField
    regarding fuzzy string lookups.
    """
    Model = TextFieldModel
