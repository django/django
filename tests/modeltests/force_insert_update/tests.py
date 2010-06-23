from django.test import TestCase

from models import Counter, WithCustomPK
from django.db import DatabaseError, IntegrityError

class ForceInsertUpdateTestCase(TestCase):
    def test_normal_case(self):
        c = Counter.objects.create(name="one", value=1)

        # The normal case
        c.value = 2
        c.save()

        # Same thing, via an update
        c.value = 3
        c.save(force_update=True)

    def test_update_and_insert_simultaneously(self):
        # Won't work because force_update and force_insert are
        # mutually exclusive
        c = Counter.objects.create(name="one", value=1)
        self.assertRaises(ValueError,
                          c.save,
                          force_insert=True, force_update=True)

    def test_update_with_no_pk(self):
        # Try to update something that doesn't have a primary key in
        # the first place.
        c1 = Counter(name="two", value=2)
        self.assertRaises(ValueError,
                          c1.save,
                          force_update=True)
        c1.save(force_insert=True)

    def test_insert_duplicate_pk(self):
        # Won't work because we can't insert a pk of the same value.
        c = Counter.objects.create(name="one", value=1)
        c.value = 2
        self.assertRaises(IntegrityError,
                          c.save,
                          force_insert=True)

    def test_nonexistent_update(self):
        # Trying to update should still fail, even with manual primary
        # keys, if the data isn't in the database already.
        obj = WithCustomPK(name=1, value=1)
        self.assertRaises(DatabaseError,
                          obj.save,
                          force_update=True)
