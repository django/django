from django import test
from collections import OrderedDict

from django.db.models.fields import related, CharField
from django.contrib.contenttypes.fields import GenericForeignKey

from .models import (
    AbstractPerson, BasePerson, Person
)

TEST_RESULTS = {
    'fields': {
        Person: [
            'id', 'data_abstract', u'fk_abstract_id',
            'data_not_concrete_abstract', u'content_type_abstract_id',
            'object_id_abstract', 'data_base', u'fk_base_id',
            'data_not_concrete_base', u'content_type_base_id',
            'object_id_base', u'baseperson_ptr_id', 'data_inherited',
            'fk_inherited_id', 'data_not_concrete_inherited',
            'content_type_concrete_id', 'object_id_concrete'],
        BasePerson: [
            'id', 'data_abstract', 'fk_abstract_id',
            'data_not_concrete_abstract', 'content_type_abstract_id',
            'object_id_abstract', 'data_base', 'fk_base_id',
            'data_not_concrete_base', 'content_type_base_id', 'object_id_base'],
        AbstractPerson: [
            'data_abstract', 'fk_abstract_id', 'data_not_concrete_abstract',
            'content_type_abstract_id', 'object_id_abstract']
    },
    'local_fields': {
        Person: [
            'baseperson_ptr_id', 'data_inherited', 'fk_inherited_id',
            'data_not_concrete_inherited', 'content_type_concrete_id',
            'object_id_concrete'],
        BasePerson: [
            'id', 'data_abstract', 'fk_abstract_id', 'data_not_concrete_abstract',
            'content_type_abstract_id', 'object_id_abstract', 'data_base',
            'fk_base_id', 'data_not_concrete_base', 'content_type_base_id',
            'object_id_base'],
        AbstractPerson: [
            'data_abstract', 'fk_abstract_id', 'data_not_concrete_abstract',
            'content_type_abstract_id', 'object_id_abstract']
    },
    'local_concrete_fields': {
        Person: [
            'baseperson_ptr_id', 'data_inherited',
            'fk_inherited_id', 'content_type_concrete_id',
            'object_id_concrete'],
        BasePerson: [
            'id', 'data_abstract',
            'fk_abstract_id', 'content_type_abstract_id',
            'object_id_abstract', 'data_base',
            'fk_base_id', 'content_type_base_id',
            'object_id_base'],
        AbstractPerson: [
            'data_abstract', 'fk_abstract_id',
            'content_type_abstract_id', 'object_id_abstract']
    },
    'many_to_many': {
        Person: [
            'm2m_abstract', 'friends_abstract',
            'following_abstract', 'm2m_base',
            'friends_base', 'following_base',
            'm2m_inherited', 'friends_inherited',
            'following_inherited'],
        BasePerson: [
            'm2m_abstract', 'friends_abstract',
            'following_abstract', 'm2m_base',
            'friends_base', 'following_base'],
        AbstractPerson: [
            'm2m_abstract', 'friends_abstract',
            'following_abstract']
    },
    'many_to_many_with_model': {
        Person: [
            BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, BasePerson,
            None, None, None],
        BasePerson: [None, None, None, None, None, None],
        AbstractPerson: [None, None, None]
    },
    'get_all_related_objects_with_model': {
        Person: (
            ['relating_baseperson', 'relating_person'],
            (BasePerson, None)),
        BasePerson: (
            ['person', 'relating_baseperson'],
            (None, None))
    },
    'get_all_related_objects_with_model_local': {
        Person: (
            ['relating_person'],
            (None,)),
        BasePerson: (
            ['person', 'relating_baseperson'],
            (None, None,))
    },
    'get_all_related_objects_with_model_hidden': {
        BasePerson: (
            [u'model_options:baseperson_friends_base',
             u'model_options:baseperson_friends_base',
             u'model_options:baseperson_m2m_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_m2m_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:person',
             u'model_options:relating_basepeople',
             u'model_options:relating_basepeople_hidden',
             u'model_options:relating',
             u'model_options:relating'],
            (None, None, None, None, None, None, None, None, None,
             None, None, None, None, None, None)),
        Person: (
            [u'model_options:baseperson_friends_base',
            u'model_options:baseperson_friends_base',
            u'model_options:baseperson_m2m_base',
            u'model_options:baseperson_following_base',
            u'model_options:baseperson_following_base',
            u'model_options:baseperson_m2m_abstract',
            u'model_options:baseperson_friends_abstract',
            u'model_options:baseperson_friends_abstract',
            u'model_options:baseperson_following_abstract',
            u'model_options:baseperson_following_abstract',
            u'model_options:relating_basepeople',
            u'model_options:relating_basepeople_hidden',
            u'model_options:relating', u'model_options:relating',
            u'model_options:person_m2m_inherited',
            u'model_options:person_friends_inherited',
            u'model_options:person_friends_inherited',
            u'model_options:person_following_inherited',
            u'model_options:person_following_inherited',
            u'model_options:relating_people',
            u'model_options:relating_people_hidden',
            u'model_options:relating', u'model_options:relating'],
            (BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, BasePerson, BasePerson,
            BasePerson, BasePerson, None, None, None, None,
            None, None, None, None, None))
    },
    'get_all_related_objects_with_model_hidden_local': {
        BasePerson: (
            [u'model_options:baseperson_friends_base',
             u'model_options:baseperson_friends_base',
             u'model_options:baseperson_m2m_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_m2m_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:person', u'model_options:relating_basepeople',
             u'model_options:relating_basepeople_hidden',
             u'model_options:relating', u'model_options:relating'],
            (None, None, None, None, None, None, None, None,
             None, None, None, None, None, None, None)),
        Person: (
            [u'model_options:person_m2m_inherited',
            u'model_options:person_friends_inherited',
            u'model_options:person_friends_inherited',
            u'model_options:person_following_inherited',
            u'model_options:person_following_inherited',
            u'model_options:relating_people',
            u'model_options:relating_people_hidden',
            u'model_options:relating',
            u'model_options:relating'],
            (None, None, None, None, None, None, None, None, None))
    },
    'get_all_related_objects_with_model_proxy': {
        BasePerson: (
            ['person', 'relating_baseperson'],
            (None, None)),
        Person: (
            ['relating_baseperson', 'relating_person', 'relating_proxyperson'],
            (BasePerson, None, None))
    },
    'get_all_related_objects_with_model_proxy_hidden': {
        BasePerson: (
            [u'model_options:baseperson_friends_base',
             u'model_options:baseperson_friends_base',
             u'model_options:baseperson_m2m_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_m2m_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:person',
             u'model_options:relating_basepeople',
             u'model_options:relating_basepeople_hidden',
             u'model_options:relating', u'model_options:relating'],
            (None, None, None, None, None, None, None, None, None,
             None, None, None, None, None, None)),
        Person: (
            [u'model_options:baseperson_friends_base',
             u'model_options:baseperson_friends_base',
             u'model_options:baseperson_m2m_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_following_base',
             u'model_options:baseperson_m2m_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_friends_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:baseperson_following_abstract',
             u'model_options:relating_basepeople',
             u'model_options:relating_basepeople_hidden',
             u'model_options:relating',
             u'model_options:relating',
             u'model_options:person_m2m_inherited',
             u'model_options:person_friends_inherited',
             u'model_options:person_friends_inherited',
             u'model_options:person_following_inherited',
             u'model_options:person_following_inherited',
             u'model_options:relating_people',
             u'model_options:relating_people_hidden',
             u'model_options:relating',
             u'model_options:relating',
             u'model_options:relating',
             u'model_options:relating'],
            (BasePerson, BasePerson, BasePerson, BasePerson,
             BasePerson, BasePerson, BasePerson, BasePerson,
             BasePerson, BasePerson, BasePerson, BasePerson,
             BasePerson, BasePerson, None, None, None, None,
             None, None, None, None, None, None, None))
    },
    'get_all_related_many_to_many_with_model': {
        BasePerson: (
            [u'friends_abstract_rel_+', 'followers_abstract',
             u'friends_base_rel_+', 'followers_base',
             'relating_basepeople', '+'],
            (None, None, None, None, None, None)),
        Person: (
            ['friends_abstract_rel_+', 'followers_abstract',
             'friends_base_rel_+', 'followers_base',
             'relating_basepeople', '+', u'friends_inherited_rel_+',
             'followers_concrete', 'relating_people', '+'],
            (BasePerson, BasePerson, BasePerson, BasePerson,
             BasePerson, BasePerson, None, None, None, None))
    },
    'get_all_related_many_to_many_local': {
        BasePerson: [
            'friends_abstract_rel_+',
            'followers_abstract',
            'friends_base_rel_+',
            'followers_base',
            'relating_basepeople',
            '+'],
        Person: [
            'friends_inherited_rel_+',
            'followers_concrete',
            'relating_people', '+']
    },
    'virtual_fields': {
        AbstractPerson: [
            'generic_relation_abstract', 'content_object_abstract'],
        BasePerson: [
            'generic_relation_base', 'content_object_base',
            'generic_relation_abstract', 'content_object_abstract'],
        Person: [
            'content_object_concrete', 'generic_relation_concrete',
            'generic_relation_base', 'content_object_base',
            'generic_relation_abstract', 'content_object_abstract']
    },
}


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
        for model, expected_result in TEST_RESULTS['fields'].items():
            fields = model._meta.fields
            self.assertEquals([f.attname for f in fields],
                              expected_result)

    def test_local_fields(self):
        for model, expected_result in TEST_RESULTS['local_fields'].items():
            fields = model._meta.local_fields
            self.assertEquals([f.attname for f in fields],
                              expected_result)
            self.assertTrue(all([f.rel is None or not isinstance(f.rel,
                            related.ManyToManyRel) for f in fields]))

    def test_local_concrete_fields(self):
        for model, expected_result in TEST_RESULTS['local_concrete_fields'].items():
            fields = model._meta.local_concrete_fields
            self.assertEquals([f.attname for f in fields],
                              expected_result)
            self.assertTrue(all([f.column is not None
                                 for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        for model, expected_result in TEST_RESULTS['many_to_many'].items():
            fields = model._meta.many_to_many
            self.assertEquals([f.attname for f in fields],
                              expected_result)
            self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                                 for f in fields]))

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            models = OrderedDict(model._meta.get_m2m_with_model()).values()
            self.assertEquals(models, expected_result)


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        k = 'get_all_related_objects_with_model'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model()
            self.eq_field_query_names_and_models(objects, expected_names,
                                                 expected_models)

    def test_related_objects_local(self):
        k = 'get_all_related_objects_with_model_local'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model(
                local_only=True)
            self.eq_field_query_names_and_models(objects, expected_names,
                                                 expected_models)

    def test_related_objects_include_hidden(self):
        k = 'get_all_related_objects_with_model_hidden'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_hidden=True)
            self.eq_field_names_and_models(objects, expected_names,
                                           expected_models)

    def test_related_objects_include_hidden_local_only(self):
        k = 'get_all_related_objects_with_model_hidden_local'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_hidden=True, local_only=True)
            self.eq_field_names_and_models(objects, expected_names,
                                           expected_models)

    def test_related_objects_proxy(self):
        k = 'get_all_related_objects_with_model_proxy'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True)
            self.eq_field_query_names_and_models(objects, expected_names,
                                                 expected_models)

    def test_related_objects_proxy_hidden(self):
        k = 'get_all_related_objects_with_model_proxy_hidden'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True, include_hidden=True)
            self.eq_field_names_and_models(objects, expected_names,
                                           expected_models)


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        k = 'get_all_related_many_to_many_with_model'
        for model, (expected_names, expected_models) in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_m2m_objects_with_model()
            fields, models = zip(*objects)
            self.eq_field_query_names_and_models(objects, expected_names,
                                                 expected_models)

    def test_related_m2m_local_only(self):
        k = 'get_all_related_many_to_many_local'
        for model, expected_names in TEST_RESULTS[k].items():
            objects = model._meta.get_all_related_many_to_many_objects(
                local_only=True)
            self.assertEquals([o.field.related_query_name()
                              for o in objects], expected_names)

    def test_related_m2m_asymmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('following_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('followers_base' in [o.field.related_query_name() for o in related_m2m])

    def test_related_m2m_symmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('friends_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('friends_inherited_rel_+' in [o.field.related_query_name() for o in related_m2m])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        for model, expected_names in TEST_RESULTS['virtual_fields'].items():
            objects = model._meta.virtual_fields
            self.assertEquals([f.name for f in objects], expected_names)


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
        field_info = Person._meta.get_field_by_name('relating_baseperson')
        self.assertEquals(field_info[1:], (BasePerson, False, False))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_related_m2m(self):
        field_info = Person._meta.get_field_by_name('relating_people')
        self.assertEquals(field_info[1:], (None, False, True))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_virtual_field(self):
        field_info = Person._meta.get_field_by_name('content_object_base')
        self.assertEquals(field_info[1:], (None, True, False))
        self.assertTrue(isinstance(field_info[0], GenericForeignKey))
