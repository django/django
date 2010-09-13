from django.db import transaction, IntegrityError, DatabaseError
from django.test import TestCase

from models import Counter, WithCustomPK


class ForceTests(TestCase):
    def test_force_update(self):
        c = Counter.objects.create(name="one", value=1)
        # The normal case

        c.value = 2
        c.save()
        # Same thing, via an update
        c.value = 3
        c.save(force_update=True)

        # Won't work because force_update and force_insert are mutually
        # exclusive
        c.value = 4
        self.assertRaises(ValueError, c.save, force_insert=True, force_update=True)

        # Try to update something that doesn't have a primary key in the first
        # place.
        c1 = Counter(name="two", value=2)
        self.assertRaises(ValueError, c1.save, force_update=True)
        c1.save(force_insert=True)

        # Won't work because we can't insert a pk of the same value.
        sid = transaction.savepoint()
        c.value = 5
        self.assertRaises(IntegrityError, c.save, force_insert=True)
        transaction.savepoint_rollback(sid)

        # Trying to update should still fail, even with manual primary keys, if
        # the data isn't in the database already.
        obj = WithCustomPK(name=1, value=1)
        self.assertRaises(DatabaseError, obj.save, force_update=True)
