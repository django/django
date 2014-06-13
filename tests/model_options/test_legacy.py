from django import test
from collections import OrderedDict

from django.db.models.fields import related, CharField
from django.contrib.contenttypes.fields import GenericForeignKey

from .models import (
    BasePerson, Person
)


class OptionsBaseTests(test.TestCase):

    def eq_field_query_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([o.field.related_query_name()
                          for o in fields], names_eq)
        self.assertEquals(models, models_eq)

    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([o.name for o in fields], names_eq)
        self.assertEquals(models, models_eq)


class DataTests(OptionsBaseTests):

    def test_fields(self):
        fields = Person._meta.fields
        self.assertEquals([f.attname for f in fields], [
                          'id', 'data_abstract', 'fk_abstract_id',
                          'data_not_concrete_abstract', 'data_base',
                          'fk_base_id', 'data_not_concrete_base',
                          'content_type_id', 'object_id',
                          'baseperson_ptr_id', 'data_inherited',
                          'fk_inherited_id', 'data_not_concrete_inherited'])

    def test_local_fields(self):
        fields = Person._meta.local_fields
        self.assertEquals([f.attname for f in fields], [
                          'baseperson_ptr_id', 'data_inherited',
                          'fk_inherited_id', 'data_not_concrete_inherited'])
        self.assertTrue(all([f.rel is None or not isinstance(f.rel,
                        related.ManyToManyRel) for f in fields]))

    def test_local_concrete_fields(self):
        fields = Person._meta.local_concrete_fields
        self.assertEquals([f.attname for f in fields], [
                          'baseperson_ptr_id', 'data_inherited',
                          'fk_inherited_id'])
        self.assertTrue(all([f.column is not None
                             for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        fields = Person._meta.many_to_many
        self.assertEquals([f.attname for f in fields], [
                          'm2m_abstract', 'm2m_base', 'friends',
                          'following', 'm2m_inherited'])
        self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                             for f in fields]))

    def test_many_to_many_with_model(self):
        models = OrderedDict(Person._meta.get_m2m_with_model()).values()
        self.assertEquals(models, [BasePerson, BasePerson, BasePerson, BasePerson, None])


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        objects = Person._meta.get_all_related_objects_with_model()
        self.eq_field_query_names_and_models(objects, [
            'relating_baseperson',
            'relating_person'
        ], (BasePerson, None))

    def test_related_objects_local(self):
        objects = Person._meta.get_all_related_objects_with_model(
            local_only=True)
        self.eq_field_query_names_and_models(objects, [
            'relating_person'
        ], (None,))

    def test_related_objects_include_hidden(self):
        objects = Person._meta.get_all_related_objects_with_model(
            include_hidden=True)
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
        objects = Person._meta.get_all_related_objects_with_model(
            include_hidden=True, local_only=True)
        self.eq_field_names_and_models(objects, [
            'model_options:person_m2m_inherited',
            'model_options:relating_people',
            'model_options:relating_people_hidden',
            'model_options:relating',
            'model_options:relating'
        ], (None, None, None, None, None))

    def test_related_objects_proxy(self):
        objects = Person._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        self.eq_field_query_names_and_models(objects, [
            'relating_baseperson',
            'relating_person',
            'relating_proxyperson'
        ], (BasePerson, None, None))

    def test_related_objects_proxy_hidden(self):
        objects = Person._meta.get_all_related_objects_with_model(
            include_proxy_eq=True, include_hidden=True)
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
        objects = Person._meta.get_all_related_m2m_objects_with_model()
        self.eq_field_names_and_models(objects, [
            u'model_options:baseperson',
            u'model_options:baseperson',
            u'model_options:relating',
            u'model_options:relating',
            u'model_options:relating',
            u'model_options:relating'
        ], (BasePerson, BasePerson, BasePerson, BasePerson, None, None))

    def test_related_m2m_local_only(self):
        objects = Person._meta.get_all_related_many_to_many_objects(
            local_only=True)
        self.assertEquals([o.field.related_query_name() for o in objects], [
            'relating_people', '+'
        ])

    def test_related_m2m_asymmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('following' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('followers' in [o.field.related_query_name() for o in related_m2m])

    def test_related_m2m_symmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('friends' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('friends_rel_+' in [o.field.related_query_name() for o in related_m2m])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        self.assertEquals([f.name for f in Person._meta.virtual_fields], [
                          'content_object'])


class GetFieldByNameTests(OptionsBaseTests):

    def test_get_data_field(self):
        field_info = Person._meta.get_field_by_name('data_abstract')
        self.assertEquals(field_info[1:], (BasePerson, True, False))
        self.assertTrue(isinstance(field_info[0], CharField))

    def test_get_m2m_field(self):
        field_info = Person._meta.get_field_by_name('m2m_base')
        self.assertEquals(field_info[1:], (BasePerson, True, True))
        self.assertTrue(isinstance(field_info[0], related.ManyToManyField))

    def test_get_related_object(self):
        field_info = Person._meta.get_field_by_name('watch')
        self.assertEquals(field_info[1:], (None, False, False))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_related_m2m(self):
        field_info = Person._meta.get_field_by_name('photo')
        self.assertEquals(field_info[1:], (None, False, True))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_virtual_field(self):
        field_info = Person._meta.get_field_by_name('content_object')
        self.assertEquals(field_info[1:], (None, True, False))
        self.assertTrue(isinstance(field_info[0], GenericForeignKey))
