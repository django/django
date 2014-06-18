from django import test
from collections import OrderedDict

from django.db.models.fields import related, CharField
from django.contrib.contenttypes.fields import GenericForeignKey

from .models import (
    AbstractPerson, BasePerson, Person, Relating, Relation
)

TEST_RESULTS = {
    'fields': {
        Person: [
            'id',
            'data_abstract',
            u'fk_abstract_id',
            'data_not_concrete_abstract',
            u'content_type_abstract_id',
            'object_id_abstract',
            'data_base',
            u'fk_base_id',
            'data_not_concrete_base',
            u'content_type_base_id',
            'object_id_base',
            u'baseperson_ptr_id',
            'data_inherited',
            'fk_inherited_id',
            'data_not_concrete_inherited',
            'content_type_concrete_id',
            'object_id_concrete'],
        BasePerson: [
            'id',
            'data_abstract',
            'fk_abstract_id',
            'data_not_concrete_abstract',
            'content_type_abstract_id',
            'object_id_abstract',
            'data_base',
            'fk_base_id',
            'data_not_concrete_base',
            'content_type_base_id',
            'object_id_base'],
        AbstractPerson: [
            'data_abstract',
            'fk_abstract_id',
            'data_not_concrete_abstract',
            'content_type_abstract_id',
            'object_id_abstract'],
        Relating: [
            'id',
            'baseperson_id',
            'baseperson_hidden_id',
            'person_id',
            'person_hidden_id',
            'proxyperson_id',
            'proxyperson_hidden_id']
    },
    'local_fields': {
        Person: [
            'baseperson_ptr_id',
            'data_inherited',
            'fk_inherited_id',
            'data_not_concrete_inherited',
            'content_type_concrete_id',
            'object_id_concrete'],
        BasePerson: [
            'id',
            'data_abstract',
            'fk_abstract_id',
            'data_not_concrete_abstract',
            'content_type_abstract_id',
            'object_id_abstract',
            'data_base',
            'fk_base_id',
            'data_not_concrete_base',
            'content_type_base_id',
            'object_id_base'],
        AbstractPerson: [
            'data_abstract',
            'fk_abstract_id',
            'data_not_concrete_abstract',
            'content_type_abstract_id',
            'object_id_abstract'],
        Relating: [
            'id',
            u'baseperson_id',
            'baseperson_hidden_id',
            'person_id',
            'person_hidden_id',
            'proxyperson_id',
            'proxyperson_hidden_id']
    },
    'local_concrete_fields': {
        Person: [
            'baseperson_ptr_id',
            'data_inherited',
            'fk_inherited_id',
            'content_type_concrete_id',
            'object_id_concrete'],
        BasePerson: [
            'id',
            'data_abstract',
            'fk_abstract_id',
            'content_type_abstract_id',
            'object_id_abstract',
            'data_base',
            'fk_base_id',
            'content_type_base_id',
            'object_id_base'],
        AbstractPerson: [
            'data_abstract',
            'fk_abstract_id',
            'content_type_abstract_id',
            'object_id_abstract'],
        Relating: [
            'id',
            'baseperson_id',
            'baseperson_hidden_id',
            'person_id',
            'person_hidden_id',
            'proxyperson_id',
            'proxyperson_hidden_id']
    },
    'many_to_many': {
        Person: [
            'm2m_abstract',
            'friends_abstract',
            'following_abstract',
            'm2m_base',
            'friends_base',
            'following_base',
            'm2m_inherited',
            'friends_inherited',
            'following_inherited'],
        BasePerson: [
            'm2m_abstract',
            'friends_abstract',
            'following_abstract',
            'm2m_base',
            'friends_base',
            'following_base'],
        AbstractPerson: [
            'm2m_abstract',
            'friends_abstract',
            'following_abstract'],
        Relating: [
            'basepeople',
            'basepeople_hidden',
            'people', 'people_hidden']
    },
    'many_to_many_with_model': {
        Person: [
            BasePerson,
            BasePerson,
            BasePerson,
            BasePerson, BasePerson, BasePerson,
            None, None, None],
        BasePerson: [
            None,
            None,
            None,
            None,
            None,
            None],
        AbstractPerson: [
            None,
            None,
            None],
        Relating: [
            None,
            None,
            None,
            None]
    },
    'get_all_related_objects_with_model': {
        Person: (
            ('relating_baseperson', BasePerson),
            ('relating_person', None)),
        BasePerson: (
            ('person', None),
            ('relating_baseperson', None)),
        Relation: (
            ('fk_abstract_rel', None),
            ('fo_abstract_rel', None),
            ('fk_base_rel', None),
            ('fo_base_rel', None),
            ('fk_concrete_rel', None),
            ('fo_concrete_rel', None)),
    },
    'get_all_related_objects_with_model_local': {
        Person: (
            ('relating_person', None),),
        BasePerson: (
            ('person', None),
            ('relating_baseperson', None)),
        Relation: (
            ('fk_abstract_rel', None),
            ('fo_abstract_rel', None),
            ('fk_base_rel', None),
            ('fo_base_rel', None),
            ('fk_concrete_rel', None),
            ('fo_concrete_rel', None)),
    },
    'get_all_related_objects_with_model_hidden': {
        BasePerson: (
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:person', None),
            (u'model_meta:relating_basepeople', None),
            (u'model_meta:relating_basepeople_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Person: (
            (u'model_meta:baseperson_friends_base', BasePerson),
            (u'model_meta:baseperson_friends_base', BasePerson),
            (u'model_meta:baseperson_m2m_base', BasePerson),
            (u'model_meta:baseperson_following_base', BasePerson),
            (u'model_meta:baseperson_following_base', BasePerson),
            (u'model_meta:baseperson_m2m_abstract', BasePerson),
            (u'model_meta:baseperson_friends_abstract', BasePerson),
            (u'model_meta:baseperson_friends_abstract', BasePerson),
            (u'model_meta:baseperson_following_abstract', BasePerson),
            (u'model_meta:baseperson_following_abstract', BasePerson),
            (u'model_meta:relating_basepeople', BasePerson),
            (u'model_meta:relating_basepeople_hidden', BasePerson),
            (u'model_meta:relating', BasePerson),
            (u'model_meta:relating', BasePerson),
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:relating_people', None),
            (u'model_meta:relating_people_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Relation: (
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None)),
    },
    'get_all_related_objects_with_model_hidden_local': {
        BasePerson: (
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:person', None),
            (u'model_meta:relating_basepeople', None),
            (u'model_meta:relating_basepeople_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Person: (
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:relating_people', None),
            (u'model_meta:relating_people_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Relation: (
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None)),
    },
    'get_all_related_objects_with_model_proxy': {
        BasePerson: (
            ('person', None),
            ('relating_baseperson', None)),
        Person: (
            ('relating_baseperson', BasePerson),
            ('relating_person', None), ('relating_proxyperson', None)),
        Relation: (
            ('fk_abstract_rel', None), ('fo_abstract_rel', None),
            ('fk_base_rel', None), ('fo_base_rel', None),
            ('fk_concrete_rel', None), ('fo_concrete_rel', None)),
    },
    'get_all_related_objects_with_model_proxy_hidden': {
        BasePerson: (
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_friends_base', None),
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_following_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_friends_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:baseperson_following_abstract', None),
            (u'model_meta:person', None),
            (u'model_meta:relating_basepeople', None),
            (u'model_meta:relating_basepeople_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Person: (
            (u'model_meta:baseperson_friends_base', BasePerson),
            (u'model_meta:baseperson_friends_base', BasePerson),
            (u'model_meta:baseperson_m2m_base', BasePerson),
            (u'model_meta:baseperson_following_base', BasePerson),
            (u'model_meta:baseperson_following_base', BasePerson),
            (u'model_meta:baseperson_m2m_abstract', BasePerson),
            (u'model_meta:baseperson_friends_abstract', BasePerson),
            (u'model_meta:baseperson_friends_abstract', BasePerson),
            (u'model_meta:baseperson_following_abstract', BasePerson),
            (u'model_meta:baseperson_following_abstract', BasePerson),
            (u'model_meta:relating_basepeople', BasePerson),
            (u'model_meta:relating_basepeople_hidden', BasePerson),
            (u'model_meta:relating', BasePerson),
            (u'model_meta:relating', BasePerson),
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_friends_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:person_following_inherited', None),
            (u'model_meta:relating_people', None),
            (u'model_meta:relating_people_hidden', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None),
            (u'model_meta:relating', None)),
        Relation: (
            (u'model_meta:baseperson_m2m_base', None),
            (u'model_meta:baseperson_m2m_abstract', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:baseperson', None),
            (u'model_meta:person_m2m_inherited', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:person', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None),
            (u'model_meta:proxyperson', None))
    },
    'get_all_related_many_to_many_with_model': {
        BasePerson: (
            (u'friends_abstract_rel_+', None),
            ('followers_abstract', None),
            (u'friends_base_rel_+', None),
            ('followers_base', None),
            ('relating_basepeople', None),
            ('+', None)),
        Person: (
            ('friends_abstract_rel_+', BasePerson),
            ('followers_abstract', BasePerson),
            ('friends_base_rel_+', BasePerson),
            ('followers_base', BasePerson),
            ('relating_basepeople', BasePerson),
            ('+', BasePerson),
            (u'friends_inherited_rel_+', None),
            ('followers_concrete', None),
            ('relating_people', None), ('+', None)),
        Relation: (
            ('m2m_abstract_rel', None),
            ('m2m_base_rel', None),
            ('m2m_concrete_rel', None)),
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
            'relating_people', '+'],
        Relation: [
            'm2m_abstract_rel',
            'm2m_base_rel', 'm2m_concrete_rel']
    },
    'virtual_fields': {
        AbstractPerson: [
            'generic_relation_abstract',
            'content_object_abstract'],
        BasePerson: [
            'generic_relation_base',
            'content_object_base',
            'generic_relation_abstract',
            'content_object_abstract'],
        Person: [
            'content_object_concrete',
            'generic_relation_concrete',
            'generic_relation_base',
            'content_object_base',
            'generic_relation_abstract',
            'content_object_abstract']
    },
}


class OptionsBaseTests(test.TestCase):

    def eq_field_query_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEqual([o.field.related_query_name()
                          for o in fields], names_eq)
        self.assertEqual(models, models_eq)

    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEqual([o.name for o in fields], names_eq)
        self.assertEqual(models, models_eq)

    def _map_rq_names(self, res):
        return tuple([(o.field.related_query_name(), m)
                for o, m in res])

    def _map_names(self, res):
        return tuple([(f.name, m) for f, m in res])


class DataTests(OptionsBaseTests):

    def test_fields(self):
        for model, expected_result in TEST_RESULTS['fields'].items():
            fields = model._meta.fields
            self.assertEqual([f.attname for f in fields], expected_result)

    def test_local_fields(self):
        for model, expected_result in TEST_RESULTS['local_fields'].items():
            fields = model._meta.local_fields
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([f.rel is None or not isinstance(f.rel,
                            related.ManyToManyRel) for f in fields]))

    def test_local_concrete_fields(self):
        for model, expected_result in TEST_RESULTS['local_concrete_fields'].items():
            fields = model._meta.local_concrete_fields
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([f.column is not None for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        for model, expected_result in TEST_RESULTS['many_to_many'].items():
            fields = model._meta.many_to_many
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                                 for f in fields]))

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            models = [model for field, model in model._meta.get_m2m_with_model()]
            self.assertEqual(models, expected_result)


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        result_key = 'get_all_related_objects_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model()
            self.assertEqual(self._map_rq_names(objects), expected)

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(local_only=True)
            self.assertEqual(self._map_rq_names(objects), expected)

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(include_hidden=True)
            self.assertEqual(self._map_names(objects), expected)

    def test_related_objects_include_hidden_local_only(self):
        result_key = 'get_all_related_objects_with_model_hidden_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_hidden=True, local_only=True)
            self.assertEqual(self._map_names(objects), expected)

    def test_related_objects_proxy(self):
        result_key = 'get_all_related_objects_with_model_proxy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True)
            self.assertEqual(self._map_rq_names(objects), expected)

    def test_related_objects_proxy_hidden(self):
        result_key = 'get_all_related_objects_with_model_proxy_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True, include_hidden=True)
            self.assertEqual(self._map_names(objects), expected)


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        result_key = 'get_all_related_many_to_many_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_m2m_objects_with_model()
            self.assertEqual(self._map_rq_names(objects), expected)

    def test_related_m2m_local_only(self):
        result_key = 'get_all_related_many_to_many_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_many_to_many_objects(
                local_only=True)
            self.assertEqual([o.field.related_query_name()
                              for o in objects], expected)

    def test_related_m2m_asymmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('following_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertTrue('followers_base' in [o.field.related_query_name() for o in related_m2m])

    def test_related_m2m_symmetrical(self):
        m2m = Person._meta.many_to_many
        self.assertTrue('friends_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_all_related_many_to_many_objects()
        self.assertIn('friends_inherited_rel_+', [o.field.related_query_name() for o in related_m2m])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        for model, expected_names in TEST_RESULTS['virtual_fields'].items():
            objects = model._meta.virtual_fields
            self.assertEqual([f.name for f in objects], expected_names)


class GetFieldByNameTests(OptionsBaseTests):

    def test_get_data_field(self):
        field_info = Person._meta.get_field_by_name('data_abstract')
        self.assertEqual(field_info[1:], (BasePerson, True, False))
        self.assertIsInstance(field_info[0], CharField)

    def test_get_m2m_field(self):
        field_info = Person._meta.get_field_by_name('m2m_base')
        self.assertEqual(field_info[1:], (BasePerson, True, True))
        self.assertIsInstance(field_info[0], related.ManyToManyField)

    def test_get_related_object(self):
        field_info = Person._meta.get_field_by_name('relating_baseperson')
        self.assertEqual(field_info[1:], (BasePerson, False, False))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_related_m2m(self):
        field_info = Person._meta.get_field_by_name('relating_people')
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_virtual_field(self):
        field_info = Person._meta.get_field_by_name('content_object_base')
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericForeignKey)
