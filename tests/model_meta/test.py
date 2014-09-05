
from django import test
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db.models import FieldDoesNotExist
from django.db.models.fields import related, CharField, Field
from django.db.models.options import IMMUTABLE_WARNING, EMPTY_RELATION_TREE

from .models import Relation, AbstractPerson, BasePerson, Person, ProxyPerson, Relating
from .results import TEST_RESULTS


class OptionsBaseTests(test.TestCase):

    def _map_related_query_names(self, res):
        return tuple((o.field.related_query_name(), m) for o, m in res)

    def _map_names(self, res):
        return tuple((f.name, m) for f, m in res)

    def _model(self, current_model, field):
        direct = isinstance(field, Field) or isinstance(field, GenericForeignKey)
        model = field.model if direct else field.parent_model._meta.concrete_model
        return None if model == current_model else model

    def _details(self, current_model, relation):
        direct = isinstance(relation, Field) or isinstance(relation, GenericForeignKey)
        model = relation.model if direct else relation.parent_model._meta.concrete_model
        if model == current_model:
            model = None

        field = relation if direct else relation.field
        m2m = isinstance(field, related.ManyToManyField)
        return relation, model, direct, m2m


class GetFieldsTests(OptionsBaseTests):

    def test_get_fields_is_immutable(self):
        for _ in range(2):
            # Running unit test twice to ensure both non-cached and cached result
            # are immutable.
            fields = Person._meta.get_fields()
            with self.assertRaises(AttributeError) as err:
                fields += ["errors"]
            self.assertEquals(str(err.exception), IMMUTABLE_WARNING)

    def test_get_fields_accepts_only_valid_kwargs(self):
        with self.assertRaises(TypeError) as err:
            Person._meta.get_fields(revese=True)
        self.assertEquals(str(err.exception), "'revese' are invalid keyword arguments")


class DataTests(OptionsBaseTests):

    def test_fields(self):
        for model, expected_result in TEST_RESULTS['fields'].items():
            fields = model._meta.fields
            self.assertEqual([f.attname for f in fields], expected_result)

    def test_local_fields(self):
        is_data_field = lambda f: isinstance(f, Field) and not isinstance(f, related.ManyToManyField)

        for model, expected_result in TEST_RESULTS['local_fields'].items():
            fields = model._meta.local_fields
            self.assertEqual([f.attname for f in fields], expected_result)
            for f in fields:
                self.assertEquals(f.model, model)
                self.assertTrue(is_data_field(f))

    def test_local_concrete_fields(self):
        for model, expected_result in TEST_RESULTS['local_concrete_fields'].items():
            fields = model._meta.local_concrete_fields
            self.assertEqual([f.attname for f in fields], expected_result)
            for f in fields:
                self.assertTrue(f.column is not None)


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        for model, expected_result in TEST_RESULTS['many_to_many'].items():
            fields = model._meta.many_to_many
            self.assertEqual([f.attname for f in fields], expected_result)
            for f in fields:
                self.assertTrue(f.has_many_values and f.has_relation)

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            models = [self._model(model, field) for field in model._meta.many_to_many]
            self.assertEqual(models, expected_result)


class RelatedObjectsTests(OptionsBaseTests):
    key_name = lambda self, r: r[0]

    def test_related_objects(self):
        result_key = 'get_all_related_objects_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(forward=False, reverse=True)
            ]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(forward=False, reverse=True, include_parents=False)
            ]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(forward=False, reverse=True, include_hidden=True)
            ]
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )

    def test_related_objects_include_hidden_local_only(self):
        result_key = 'get_all_related_objects_with_model_hidden_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(forward=False, reverse=True, include_hidden=True, include_parents=False)
            ]
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        for model, expected_names in TEST_RESULTS['virtual_fields'].items():
            objects = model._meta.virtual_fields
            self.assertEqual(sorted([f.name for f in objects]), sorted(expected_names))


class GetFieldByNameTests(OptionsBaseTests):

    def test_get_data_field(self):
        field_info = self._details(Person, Person._meta.get_field('data_abstract'))
        self.assertEqual(field_info[1:], (BasePerson, True, False))
        self.assertIsInstance(field_info[0], CharField)

    def test_get_m2m_field(self):
        field_info = self._details(Person, Person._meta.get_field('m2m_base'))
        self.assertEqual(field_info[1:], (BasePerson, True, True))
        self.assertIsInstance(field_info[0], related.ManyToManyField)

    def test_get_related_object(self):
        field_info = self._details(Person, Person._meta.get_field('relating_baseperson', include_related=True))
        self.assertEqual(field_info[1:], (BasePerson, False, False))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_related_m2m(self):
        field_info = self._details(Person, Person._meta.get_field('relating_people', include_related=True))
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_generic_foreign_key(self):
        # For historic reasons generic foreign keys aren't available.
        with self.assertRaises(FieldDoesNotExist):
            Person._meta.get_field('content_object_base', virtual=True)

    def test_get_generic_relation(self):
        field_info = self._details(Person, Person._meta.get_field('generic_relation_base'))
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericRelation)


class RelationTreeTests(test.TestCase):
    all_models = (Relation, AbstractPerson, BasePerson, Person, ProxyPerson, Relating)

    def setUp(self):
        apps.clear_cache()

    def test_clear_cache_clears_relation_tree(self):
        # the apps.clear_cache is setUp() should have deleted all trees.
        for m in self.all_models:
            self.assertNotIn('relation_tree', m._meta.__dict__)

    def test_first_relation_tree_access_populates_all(self):
        # On first access, relation tree should have populated cache.
        self.assertTrue(self.all_models[0]._meta.relation_tree)

        # AbstractPerson does not have any relations, so relation_tree
        # should just return an EMPTY_RELATION_TREE.
        self.assertEquals(
            AbstractPerson._meta.relation_tree,
            EMPTY_RELATION_TREE
        )

        # All the other models should already have their relation tree
        # in the internal __dict__ .
        all_models_but_abstractperson = (m for m in self.all_models if m is not AbstractPerson)
        for m in all_models_but_abstractperson:
            self.assertIn('relation_tree', m._meta.__dict__)

    def test_relations_related_objects(self):

        # Testing non hidden related objects

        self.assertEqual(
            sorted([field.related_query_name() for field in Relation._meta.relation_tree
                   if not field.related.field.rel.is_hidden()]),
            sorted(['fk_abstract_rel', 'fk_abstract_rel', 'fk_abstract_rel', 'fk_base_rel', 'fk_base_rel',
                    'fk_base_rel', 'fk_concrete_rel', 'fk_concrete_rel', 'fo_abstract_rel', 'fo_abstract_rel',
                    'fo_abstract_rel', 'fo_base_rel', 'fo_base_rel', 'fo_base_rel', 'fo_concrete_rel',
                    'fo_concrete_rel', 'm2m_abstract_rel', 'm2m_abstract_rel', 'm2m_abstract_rel',
                    'm2m_base_rel', 'm2m_base_rel', 'm2m_base_rel', 'm2m_concrete_rel', 'm2m_concrete_rel'])
        )

        # Testing hidden related objects
        self.assertEqual(
            sorted([field.related_query_name() for field in BasePerson._meta.relation_tree]),
            sorted(['+', '+', 'BasePerson_following_abstract+', 'BasePerson_following_abstract+',
                    'BasePerson_following_base+', 'BasePerson_following_base+', 'BasePerson_friends_abstract+',
                    'BasePerson_friends_abstract+', 'BasePerson_friends_base+', 'BasePerson_friends_base+',
                    'BasePerson_m2m_abstract+', 'BasePerson_m2m_base+', 'Relating_basepeople+',
                    'Relating_basepeople_hidden+', 'followers_abstract', 'followers_abstract', 'followers_abstract',
                    'followers_base', 'followers_base', 'followers_base', 'friends_abstract_rel_+', 'friends_abstract_rel_+',
                    'friends_abstract_rel_+', 'friends_base_rel_+', 'friends_base_rel_+', 'friends_base_rel_+', 'person',
                    'person', 'relating_basepeople', 'relating_baseperson'])
        )
        self.assertEqual([field.related_query_name() for field in AbstractPerson._meta.relation_tree], [])

    def test_no_cache_option(self):

        # Expire all get_fields cache
        related_models = [Person, BasePerson, AbstractPerson]
        for model in related_models:
            model._meta._expire_cache()

        for model in related_models:
            self.assertEqual(0, len(model._meta._get_fields_cache.keys()))

        # Make an API call with cache_results=False, it should not store
        # results on any of the children.
        Person._meta.get_fields(cache_results=False)
        for model in related_models:
            for c in model._meta._get_fields_cache.keys():
                self.assertEqual(0, len(model._meta._get_fields_cache.keys()))
