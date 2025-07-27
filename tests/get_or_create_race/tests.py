from django.test import TransactionTestCase
from django.db import connection
from concurrent.futures import ThreadPoolExecutor
from .models import Parent, Child
import unittest


@unittest.skipUnless(
    connection.vendor == "postgresql", "This test only runs on PostgreSQL"
)
class GetOrCreateRaceTest(TransactionTestCase):
    available_apps = ["get_or_create_race"]
    reset_sequences = True

    def test_get_or_create_race_does_not_corrupt_relation(self):
        parent = Parent.objects.create(name="parent")

        def create_child():
            # Two threads trying to create a child with the same parent
            return Child.objects.get_or_create(parent=Parent.objects.get(pk=parent.pk))

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda _: create_child(), range(2)))

        children = Child.objects.filter(parent=parent)
        self.assertEqual(
            children.count(), 1, msg=f"Expected 1 child, got {children.count()}"
        )

        # Also ensure the reverse relation works
        self.assertEqual(parent.child.pk, children.first().pk)
