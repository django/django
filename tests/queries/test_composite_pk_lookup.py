import unittest

from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps


@isolate_apps("queries")
class CompositePKLookupTests(TestCase):
    class CompositePrimaryKeyModel(models.Model):
        tenant_id = models.IntegerField()
        code = models.CharField(max_length=10)
        label = models.CharField(max_length=50, default="")

        class Meta:
            app_label = "queries"
            constraints = [
                models.UniqueConstraint(
                    fields=["tenant_id", "code"], name="composite_pk"
                )
            ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = cls.CompositePrimaryKeyModel.objects.create(
            tenant_id=1, code="A", label="alpha"
        )

    @unittest.expectedFailure
    def test_pk_in_with_partial_or_all_none(self):
        test_cases = [
            ("filter", [(1, None)]),
            ("filter", [(None, None)]),
            ("exclude", [(1, None)]),
            ("exclude", [(None, None)]),
        ]

        for method, value in test_cases:
            with self.subTest(method=method, value=value):
                try:
                    qs = getattr(self.CompositePrimaryKeyModel.objects, method)(
                        pk__in=value
                    )
                    list(qs)  # force eval
                except Exception as e:
                    self.fail(f"{method}(pk__in={value}) raised: {e}")
