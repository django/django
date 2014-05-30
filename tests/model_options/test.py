from django import test

from django.contrib.auth.models import (
    User, Permission
)
from django.db.models.options import (
    DATA, LOCAL_ONLY, M2M, CONCRETE, RELATED_OBJECTS, INCLUDE_PROXY,
    RELATED_M2M
)

from .models import (
    Person, Quartet, Group, Reporter, Musician,
    SuperData, SuperM2MModel
)


class OptionsBaseTests(test.TestCase):

    def get_fields(self, Model, **kwargs):
        return Model._meta.get_new_fields(**kwargs)

    def map_model(self, new_fields):
        return [f for n, f in new_fields]

    def assertEqualFields(self, old_fields, new_fields):
        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, uniq_old_fields)


class DataTests(OptionsBaseTests):

    def test_data_local(self):
        new_fields = self.get_fields(SuperData, types=DATA, opts=LOCAL_ONLY)
        old_fields = SuperData._meta.local_fields
        self.assertEqual(old_fields, self.map_model(new_fields))

    def test_data(self):
        new_fields = self.get_fields(SuperData, types=DATA)
        old_fields = SuperData._meta.get_fields_with_model()
        self.assertEqualFields(old_fields, new_fields)

    def test_data_local_concrete(self):
        new_fields = self.get_fields(SuperData, types=DATA,
                                     opts=LOCAL_ONLY | CONCRETE)
        old_fields = SuperData._meta.local_concrete_fields
        self.assertEqual(old_fields, self.map_model(new_fields))

    def test_data_concrete(self):
        new_fields = self.get_fields(SuperData, types=DATA, opts=CONCRETE)
        old_fields = SuperData._meta.concrete_fields
        self.assertEqual(old_fields, self.map_model(new_fields))


class M2MTests(OptionsBaseTests):

    def test_m2m(self):
        new_fields = self.get_fields(SuperM2MModel, types=M2M)
        old_fields = SuperM2MModel._meta.get_m2m_with_model()
        self.assertEqualFields(old_fields, new_fields)

    def test_m2m_local(self):
        new_fields = self.get_fields(SuperM2MModel, types=M2M,
                                     opts=LOCAL_ONLY)
        old_fields = SuperM2MModel._meta.local_many_to_many
        self.assertEqual(old_fields, self.map_model(new_fields))


class OptionsTests(OptionsBaseTests):

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
        models = [User, Permission]
        for M in models:
            old_fields = M._meta.get_all_related_objects_with_model(
                False, False, False)
            new_fields = M._meta.get_new_fields(types=RELATED_OBJECTS)

            uniq_old_fields = [x for x, y in old_fields]
            uniq_new_fields = [y for x, y in new_fields]

            self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_objects_proxy(self):
        # Without proxy
        old_fields = Reporter._meta.get_all_related_objects_with_model()
        new_fields = Reporter._meta.get_new_fields(types=RELATED_OBJECTS)
        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, uniq_old_fields)

        # With proxy
        old_fields = Reporter._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        new_fields = Reporter._meta.get_new_fields(types=RELATED_OBJECTS,
                                                   opts=INCLUDE_PROXY)
        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_objects_local_only(self):
        old_fields = Quartet._meta.get_all_related_objects_with_model(
            True, False, False)
        new_fields = Quartet._meta.get_new_fields(types=RELATED_OBJECTS,
                                                  opts=LOCAL_ONLY)
        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]

        self.assertEquals(uniq_new_fields, uniq_old_fields)

    def test_related_m2m_objects(self):
        old_fields = Musician._meta.get_all_related_many_to_many_objects()
        new_fields = Musician._meta.get_new_fields(types=RELATED_M2M)
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, old_fields)
