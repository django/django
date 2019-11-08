from django.contrib.postgres.search import TrigramDistance, TrigramSimilarity
from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import CharFieldModel, TextFieldModel


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class TrigramTest(PostgreSQLTestCase):
    Model = CharFieldModel

    @classmethod
    def setUpTestData(cls):
        cls.Model.objects.bulk_create([
            cls.Model(field='Matthew'),
            cls.Model(field='Cat sat on mat.'),
            cls.Model(field='Dog sat on rug.'),
        ])

    def test_trigram_search(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__trigram_similar='Mathew'),
            ['Matthew'],
            transform=lambda instance: instance.field,
        )

    def test_trigram_similarity(self):
        search = 'Bat sat on cat.'
        # Round result of similarity because PostgreSQL 12+ uses greater
        # precision.
        self.assertQuerysetEqual(
            self.Model.objects.filter(
                field__trigram_similar=search,
            ).annotate(similarity=TrigramSimilarity('field', search)).order_by('-similarity'),
            [('Cat sat on mat.', 0.625), ('Dog sat on rug.', 0.333333)],
            transform=lambda instance: (instance.field, round(instance.similarity, 6)),
            ordered=True,
        )

    def test_trigram_similarity_alternate(self):
        # Round result of distance because PostgreSQL 12+ uses greater
        # precision.
        self.assertQuerysetEqual(
            self.Model.objects.annotate(
                distance=TrigramDistance('field', 'Bat sat on cat.'),
            ).filter(distance__lte=0.7).order_by('distance'),
            [('Cat sat on mat.', 0.375), ('Dog sat on rug.', 0.666667)],
            transform=lambda instance: (instance.field, round(instance.distance, 6)),
            ordered=True,
        )


class TrigramTextFieldTest(TrigramTest):
    """
    TextField has the same behavior as CharField regarding trigram lookups.
    """
    Model = TextFieldModel
