from django import test
from django.db.models.options import DATA, LOCAL_ONLY, M2M, CONCRETE

from .models import Person, Quartet


class OptionsTests(test.TestCase):
    def test_fields(self):
        new_fields = Quartet._meta.get_new_fields(types=DATA)
        old_fields = Quartet._meta.fields
        self.assertEquals(old_fields, [x[1] for x in new_fields])

    def test_concrete_fields(self):
        new_fields = Person._meta.get_new_fields(types=DATA, opts=CONCRETE)
        old_fields = Person._meta.concrete_fields
        self.assertEquals(old_fields, [x[1] for x in new_fields])

    def test_local_concrete_fields(self):
        new_fields = Person._meta.get_new_fields(types=DATA, opts=CONCRETE | LOCAL_ONLY)
        old_fields = Person._meta.local_concrete_fields
        self.assertEquals(old_fields, [x[1] for x in new_fields])

    def test_local_fields(self):
        new_fields = Quartet._meta.get_new_fields(types=DATA, opts=LOCAL_ONLY)
        old_fields = ((Quartet._meta.local_fields[0].attname,
                      Quartet._meta.local_fields[0]),)
        self.assertEquals(new_fields, old_fields)

    def test_many_to_many(self):
        new_fields = Quartet._meta.get_new_fields(types=M2M)
        old_fields = Quartet._meta.many_to_many
        self.assertEquals(old_fields, [x[1] for x in new_fields])
