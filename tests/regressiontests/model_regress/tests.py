from django.core.exceptions import ValidationError
from django.test import TestCase

from models import Worker, NonAutoPK


class RelatedModelOrderedLookupTest(TestCase):
    """
    Regression test for #10153: foreign key __gte and __lte lookups.
    """

    # The bug is that the following queries would raise:
    # "TypeError: Related Field has invalid lookup: gte"

    def test_related_gte_lookup(self):
        Worker.objects.filter(department__gte=0)

    def test_related_lte_lookup(self):
        Worker.objects.filter(department__lte=0)


class ModelValidationTest(TestCase):
    def test_pk_validation(self):
        one = NonAutoPK.objects.create(name="one")
        again = NonAutoPK(name="one")
        self.assertRaises(ValidationError, again.validate_unique)
