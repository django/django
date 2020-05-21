from django.db import NotSupportedError
from django.test import TransactionTestCase

from .models import Person


class SelectForCommonTests(TransactionTestCase):
    available_apps = ["select_for"]

    def test_exclusivity_in_query(self):
        qs = Person.objects.all()
        qs.query.select_for_share = True
        qs.query.select_for_update = True
        msg = "Cannot use FOR SHARE and FOR UPDATE in the same query."
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(qs)

    def test_exclusivity_in_queryset(self):
        msg = "Cannot call select_for_update() after select_for_share()."
        with self.assertRaisesMessage(TypeError, msg):
            Person.objects.select_for_share().select_for_update()

        msg = "Cannot call select_for_share() after select_for_update()."
        with self.assertRaisesMessage(TypeError, msg):
            Person.objects.select_for_update().select_for_share()
