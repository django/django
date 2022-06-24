from django.test import TestCase
from django.db.models import Count, Q, F

from .models import FirstModel


class QueryDoesNotFail(TestCase):
    """This query is broken in Django 3.2
    https://code.djangoproject.com/ticket/33808
    """

    def test_broken(self):
        queryset = FirstModel.objects.annotate(
            howmany=Count(Q(sm_f1__in=F("sm_f2"))),
        )
        try:
            self.assertEqual(queryset.count(), 0)
        except Exception:
            self.fail("This query failed to execute.")
