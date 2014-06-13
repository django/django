from django import test
from collections import OrderedDict

from django.db.models.fields import related, CharField
from django.contrib.contenttypes.fields import GenericForeignKey

from django.db.models.options import (
    DATA, M2M as _M2M, RELATED_OBJECTS, RELATED_M2M, VIRTUAL,
    LOCAL_ONLY, CONCRETE, INCLUDE_PROXY, INCLUDE_HIDDEN, NONE
)

from .models import (
    BasePerson, Person, ProxyPerson
)


class OptionsBaseTests(test.TestCase):
    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([f.name for f in fields], names_eq)
        self.assertEquals(models, models_eq)

    def eq_field_query_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([o.field.related_query_name()
                          for o in fields], names_eq)
        self.assertEquals(models, models_eq)

    def fields(self, res):
        return [f for fn, f in res]

    def fields_models(self, m, res):

        def get_model(field):
            from django.db.models import Field
            from django.contrib.contenttypes.fields import GenericForeignKey
            direct = isinstance(field, Field) or isinstance(field, GenericForeignKey)

            model = field.model if direct else field.parent_model._meta.concrete_model
            model = None if model == m else model
            return (field, model)

        return map(get_model, res)

    def _map_none(self, m, res):
        res = list(res)
        if res[1] == m:
            res[1] = None
        return tuple(res)


class DataTests(OptionsBaseTests):

    def test_fields(self):
        fields = Person._meta.get_new_fields(types=DATA)
        self.assertEquals([f.attname for f in fields], [
                          u'id', 'data_abstract', u'fk_abstract_id',
                          'data_not_concrete_abstract', u'content_type_abstract_id',
                          'object_id_abstract', 'data_base', u'fk_base_id',
                          'data_not_concrete_base', u'content_type_base_id',
                          'object_id_base', u'baseperson_ptr_id', 'data_inherited',
                          u'fk_inherited_id', 'data_not_concrete_inherited',
                          u'content_type_concrete_id', 'object_id_concrete'])

    def test_local_fields(self):
        fields = Person._meta.get_new_fields(types=DATA, opts=LOCAL_ONLY)
        self.assertEquals([f.attname for f in fields], [
                          'baseperson_ptr_id', 'data_inherited',
                          'fk_inherited_id', 'data_not_concrete_inherited',
                          'content_type_concrete_id', 'object_id_concrete'])
        self.assertTrue(all([f.rel is None or not isinstance(f.rel,
                        related.ManyToManyRel) for f in fields]))

    def test_local_concrete_fields(self):
        fields = Person._meta.get_new_fields(types=DATA,
                                             opts=LOCAL_ONLY | CONCRETE)
        self.assertEquals([f.attname for f in fields], [
                          'baseperson_ptr_id', 'data_inherited',
                          'fk_inherited_id', 'content_type_concrete_id',
                          'object_id_concrete'])
        self.assertTrue(all([f.column is not None
                             for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        fields = Person._meta.get_new_fields(types=_M2M)
        self.assertEquals([f.attname for f in fields], [
                          'm2m_abstract', 'm2m_base', 'friends',
                          'following', 'm2m_inherited'])
        self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                             for f in fields]))

    def test_many_to_many_with_model(self):
        models = self.fields_models(Person, Person._meta.get_new_fields(types=_M2M))
        self.assertEquals([m for f, m in models], [BasePerson, BasePerson, BasePerson, BasePerson, None])


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS))
        self.eq_field_query_names_and_models(objects, [
            'relating_baseperson',
            'relating_person'
        ], (BasePerson, None))

    def test_related_objects_local(self):
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=LOCAL_ONLY))
        self.eq_field_query_names_and_models(objects, [
            'relating_person'
        ], (None,))

    def test_related_objects_include_hidden(self):
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=INCLUDE_HIDDEN))
        self.eq_field_names_and_models(objects, [
            'model_options:baseperson_m2m_base',
            'model_options:baseperson_following',
            'model_options:baseperson_following',
            'model_options:baseperson_friends',
            'model_options:baseperson_friends',
            'model_options:baseperson_m2m_abstract',
            'model_options:relating_basepeople',
            'model_options:relating_basepeople_hidden',
            'model_options:relating',
            'model_options:relating',
            'model_options:person_m2m_inherited',
            'model_options:relating_people',
            'model_options:relating_people_hidden',
            'model_options:relating',
            'model_options:relating'
        ], (BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, None, None, None, None, None))

    def test_related_objects_include_hidden_local_only(self):
        opts = INCLUDE_HIDDEN | LOCAL_ONLY
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=opts))
        self.eq_field_names_and_models(objects, [
            'model_options:person_m2m_inherited',
            'model_options:relating_people',
            'model_options:relating_people_hidden',
            'model_options:relating',
            'model_options:relating'
        ], (None, None, None, None, None))

    def test_related_objects_proxy(self):
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=INCLUDE_PROXY))
        self.eq_field_query_names_and_models(objects, [
            'relating_baseperson',
            'relating_person',
            'relating_proxyperson'
        ], (BasePerson, None, None))

    def test_related_objects_proxy_hidden(self):
        opts = INCLUDE_HIDDEN | INCLUDE_PROXY
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=opts))
        self.eq_field_names_and_models(objects, [
            'model_options:baseperson_m2m_base',
            'model_options:baseperson_following',
            'model_options:baseperson_following',
            'model_options:baseperson_friends',
            'model_options:baseperson_friends',
            'model_options:baseperson_m2m_abstract',
            'model_options:relating_basepeople',
            'model_options:relating_basepeople_hidden',
            'model_options:relating',
            'model_options:relating',
            'model_options:person_m2m_inherited',
            'model_options:relating_people',
            'model_options:relating_people_hidden',
            'model_options:relating',
            'model_options:relating',
            'model_options:relating',
            'model_options:relating'
        ], (BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, None, None, None, None, None, None, None))


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        objects = self.fields_models(Person, Person._meta.get_new_fields(
                                     types=RELATED_M2M))
        self.eq_field_names_and_models(objects, [
            u'model_options:baseperson',
            u'model_options:baseperson',
            u'model_options:relating',
            u'model_options:relating',
            u'model_options:relating',
            u'model_options:relating'
        ], (BasePerson, BasePerson, BasePerson, BasePerson, None, None))

    def test_related_m2m_local_only(self):
        objects = Person._meta.get_new_fields(types=RELATED_M2M,
                                              opts=LOCAL_ONLY)
        self.assertEquals([o.field.related_query_name() for o in objects], [
            'relating_people', '+'
        ])

    def test_related_m2m_asymmetrical(self):
        m2m = Person._meta.get_new_fields(types=_M2M)
        self.assertTrue('following' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('followers' in [o.field.related_query_name() for o in related_m2m])

    def test_related_m2m_symmetrical(self):
        m2m = Person._meta.get_new_fields(types=_M2M)
        self.assertTrue('friends' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('friends_rel_+' in [o.field.related_query_name() for o in related_m2m])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        self.assertEquals([fn for fn, f in Virtual._meta.get_new_fields(types=VIRTUAL)], [
                          'content_object'])


class GetFieldByNameTests(OptionsBaseTests):

    def test_get_data_field(self):
        field_info = self._map_none(Data, Data._meta.get_field_details('name_abstract'))
        self.assertEquals(field_info[1:], (BaseData, True, False))
        self.assertTrue(isinstance(field_info[0], CharField))

    def test_get_m2m_field(self):
        field_info = self._map_none(M2M, M2M._meta.get_field_details('m2m_base'))
        self.assertEquals(field_info[1:], (BaseM2M, True, True))
        self.assertTrue(isinstance(field_info[0], related.ManyToManyField))

    def test_get_related_object(self):
        field_info = self._map_none(RelatedObject, RelatedObject._meta.get_field_details('relrelatedobjects'))
        self.assertEquals(field_info[1:], (None, False, False))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_related_m2m(self):
        field_info = self._map_none(RelatedM2M, RelatedM2M._meta.get_field_details('relrelatedm2m'))
        self.assertEquals(field_info[1:], (None, False, True))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_virtual_field(self):
        field_info = self._map_none(Virtual, Virtual._meta.get_field_details('content_object'))
        self.assertEquals(field_info[1:], (None, True, False))
        self.assertTrue(isinstance(field_info[0], GenericForeignKey))
