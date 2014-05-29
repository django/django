from django import test

from django.contrib.auth.models import (
    User, Permission, Group
)
from django.db.models.options import (
    DATA, LOCAL_ONLY, M2M, CONCRETE, RELATED_OBJECTS, INCLUDE_PROXY
)

from .models import Person, Quartet, Group, Reporter


class OptionsTests(test.TestCase):

    def setUp(self):
        for c in['_related_objects_proxy_cache',
                 '_related_objects_cache']:
            try:
                delattr(Group, c)
            except AttributeError:
                pass

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

    def test_related_objects(self):
        del Group._meta._related_objects_cache
        del Group._meta._related_objects_proxy_cache
        old_fields = Group._meta.get_all_related_objects_with_model(
            False, False, False)
        new_fields = Group._meta.get_new_fields(types=RELATED_OBJECTS)

        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]

        self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_objects_2(self):
        old_fields = Quartet._meta.get_all_related_objects_with_model(
            False, False, False)
        new_fields = Quartet._meta.get_new_fields(types=RELATED_OBJECTS)

        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]

        self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_objects_contrib_auth(self):
        models = [User, Permission, Group]
        for M in models:
            old_fields = M._meta.get_all_related_objects_with_model(
                False, False, False)
            new_fields = M._meta.get_new_fields(types=RELATED_OBJECTS)

            uniq_old_fields = [x for x, y in old_fields]
            uniq_new_fields = [y for x, y in new_fields]

            self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_objects_proxy(self):
        old_fields = Reporter._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        new_fields = Reporter._meta.get_new_fields(
                        types=RELATED_OBJECTS, opts=INCLUDE_PROXY)

        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]

        self.assertEquals(uniq_new_fields, uniq_old_fields)

    #def test_related_objects_local_only(self):
        #old_fields = Quartet._meta.get_all_related_objects_with_model(
            #True, False, False)
        #new_fields = Quartet._meta.get_new_fields(types=RELATED_OBJECTS,
                                                  #opts=LOCAL_ONLY)
        #self.assertEquals(old_fields, new_fields)
