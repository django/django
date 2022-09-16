from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import CharFieldModel, TextFieldModel

try:
    from django.contrib.postgres.search import (
        TrigramDistance,
        TrigramSimilarity,
        TrigramStrictWordDistance,
        TrigramStrictWordSimilarity,
        TrigramWordDistance,
        TrigramWordSimilarity,
    )
except ImportError:
    pass


@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class TrigramTest(PostgreSQLTestCase):
    Model = CharFieldModel

    @classmethod
    def setUpTestData(cls):
        cls.Model.objects.bulk_create(
            [
                cls.Model(field="Matthew"),
                cls.Model(field="Cat sat on mat."),
                cls.Model(field="Dog sat on rug."),
            ]
        )

    def test_trigram_search(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__trigram_similar="Mathew"),
            ["Matthew"],
            transform=lambda instance: instance.field,
        )

    def test_trigram_word_search(self):
        obj = self.Model.objects.create(
            field="Gumby rides on the path of Middlesbrough",
        )
        self.assertSequenceEqual(
            self.Model.objects.filter(field__trigram_word_similar="Middlesborough"),
            [obj],
        )
        self.assertSequenceEqual(
            self.Model.objects.filter(field__trigram_word_similar="Middle"),
            [obj],
        )

    def test_trigram_strict_word_search_matched(self):
        obj = self.Model.objects.create(
            field="Gumby rides on the path of Middlesbrough",
        )
        self.assertSequenceEqual(
            self.Model.objects.filter(
                field__trigram_strict_word_similar="Middlesborough"
            ),
            [obj],
        )
        self.assertSequenceEqual(
            self.Model.objects.filter(field__trigram_strict_word_similar="Middle"),
            [],
        )

    def test_trigram_similarity(self):
        search = "Bat sat on cat."
        # Round result of similarity because PostgreSQL uses greater precision.
        self.assertQuerysetEqual(
            self.Model.objects.filter(
                field__trigram_similar=search,
            )
            .annotate(similarity=TrigramSimilarity("field", search))
            .order_by("-similarity"),
            [("Cat sat on mat.", 0.625), ("Dog sat on rug.", 0.333333)],
            transform=lambda instance: (instance.field, round(instance.similarity, 6)),
            ordered=True,
        )

    def test_trigram_word_similarity(self):
        search = "mat"
        self.assertSequenceEqual(
            self.Model.objects.filter(
                field__trigram_word_similar=search,
            )
            .annotate(
                word_similarity=TrigramWordSimilarity(search, "field"),
            )
            .values("field", "word_similarity")
            .order_by("-word_similarity"),
            [
                {"field": "Cat sat on mat.", "word_similarity": 1.0},
                {"field": "Matthew", "word_similarity": 0.75},
            ],
        )

    def test_trigram_strict_word_similarity(self):
        search = "matt"
        self.assertSequenceEqual(
            self.Model.objects.filter(field__trigram_word_similar=search)
            .annotate(word_similarity=TrigramStrictWordSimilarity(search, "field"))
            .values("field", "word_similarity")
            .order_by("-word_similarity"),
            [
                {"field": "Cat sat on mat.", "word_similarity": 0.5},
                {"field": "Matthew", "word_similarity": 0.44444445},
            ],
        )

    def test_trigram_similarity_alternate(self):
        # Round result of distance because PostgreSQL uses greater precision.
        self.assertQuerysetEqual(
            self.Model.objects.annotate(
                distance=TrigramDistance("field", "Bat sat on cat."),
            )
            .filter(distance__lte=0.7)
            .order_by("distance"),
            [("Cat sat on mat.", 0.375), ("Dog sat on rug.", 0.666667)],
            transform=lambda instance: (instance.field, round(instance.distance, 6)),
            ordered=True,
        )

    def test_trigram_word_similarity_alternate(self):
        self.assertSequenceEqual(
            self.Model.objects.annotate(
                word_distance=TrigramWordDistance("mat", "field"),
            )
            .filter(
                word_distance__lte=0.7,
            )
            .values("field", "word_distance")
            .order_by("word_distance"),
            [
                {"field": "Cat sat on mat.", "word_distance": 0},
                {"field": "Matthew", "word_distance": 0.25},
            ],
        )

    def test_trigram_strict_word_distance(self):
        self.assertSequenceEqual(
            self.Model.objects.annotate(
                word_distance=TrigramStrictWordDistance("matt", "field"),
            )
            .filter(word_distance__lte=0.7)
            .values("field", "word_distance")
            .order_by("word_distance"),
            [
                {"field": "Cat sat on mat.", "word_distance": 0.5},
                {"field": "Matthew", "word_distance": 0.5555556},
            ],
        )


class TrigramTextFieldTest(TrigramTest):
    """
    TextField has the same behavior as CharField regarding trigram lookups.
    """

    Model = TextFieldModel
