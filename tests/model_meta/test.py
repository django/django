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
        return tuple((o.name, m) for o, m in res)

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
            self.assertEqual(str(err.exception), IMMUTABLE_WARNING % "get_fields()")

    def test_get_fields_accepts_only_valid_kwargs(self):
        with self.assertRaises(TypeError) as err:
            Person._meta.get_fields(revese=True)
        self.assertEqual(str(err.exception), "'revese' are invalid keyword arguments")


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
                self.assertEqual(f.model, model)
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
                for field in model._meta.get_fields()
                if field.is_reverse_object
            ]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(include_parents=False)
                if field.is_reverse_object
            ]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(include_hidden=True)
                if field.is_reverse_object
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
                for field in model._meta.get_fields(include_hidden=True, include_parents=False)
                if field.is_reverse_object
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
        field_info = self._details(Person, Person._meta.get_field('relating_baseperson'))
        self.assertEqual(field_info[1:], (BasePerson, False, False))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_related_m2m(self):
        field_info = self._details(Person, Person._meta.get_field('relating_people'))
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_generic_relation(self):
        field_info = self._details(Person, Person._meta.get_field('generic_relation_base'))
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericRelation)

    def test_get_fields_only_searaches_forward_on_apps_not_ready(self):
        opts = Person._meta

        # If apps registry is not ready, get_field() searches
        # over only forward fields.
        opts.apps.ready = False

        # 'data_abstract' is a forward field, and therefore will be found
        self.assertTrue(opts.get_field('data_abstract'))

        message = "Person has no field named 'relating_baseperson'. The app cache " \
                  "isn't ready yet, so if this is a forward field, it won't be " \
                  "available yet."

        # 'data_abstract' is a reverse field, and will raise an exception
        with self.assertRaises(FieldDoesNotExist) as err:
            opts.get_field('relating_baseperson')
        self.assertEqual(str(err.exception), message)

        opts.apps.ready = True


class RelationTreeTests(test.TestCase):
    all_models = (Relation, AbstractPerson, BasePerson, Person, ProxyPerson, Relating)

    def setUp(self):
        apps.clear_cache(True)

    def test_clear_cache_clears_relation_tree(self):
        # the apps.clear_cache is setUp() should have deleted all trees.
        for m in self.all_models:
            self.assertNotIn('_relation_tree', m._meta.__dict__)

    def test_first_relation_tree_access_populates_all(self):
        # On first access, relation tree should have populated cache.
        self.assertTrue(self.all_models[0]._meta._relation_tree)

        # AbstractPerson does not have any relations, so relation_tree
        # should just return an EMPTY_RELATION_TREE.
        self.assertEqual(
            AbstractPerson._meta._relation_tree,
            EMPTY_RELATION_TREE
        )

        # All the other models should already have their relation tree
        # in the internal __dict__ .
        all_models_but_abstractperson = (m for m in self.all_models if m is not AbstractPerson)
        for m in all_models_but_abstractperson:
            self.assertIn('_relation_tree', m._meta.__dict__)

    def test_relations_related_objects(self):

        # Testing non hidden related objects

        self.assertEqual(
            sorted([field.related_query_name() for field in Relation._meta._relation_tree
                   if not field.related.field.rel.is_hidden()]),
            sorted(['fk_abstract_rel', 'fk_abstract_rel', 'fk_abstract_rel', 'fk_base_rel', 'fk_base_rel',
                    'fk_base_rel', 'fk_concrete_rel', 'fk_concrete_rel', 'fo_abstract_rel', 'fo_abstract_rel',
                    'fo_abstract_rel', 'fo_base_rel', 'fo_base_rel', 'fo_base_rel', 'fo_concrete_rel',
                    'fo_concrete_rel', 'm2m_abstract_rel', 'm2m_abstract_rel', 'm2m_abstract_rel',
                    'm2m_base_rel', 'm2m_base_rel', 'm2m_base_rel', 'm2m_concrete_rel', 'm2m_concrete_rel'])
        )

        # Testing hidden related objects
        self.assertEqual(
            sorted([field.related_query_name() for field in BasePerson._meta._relation_tree]),
            sorted(['+', '+', 'BasePerson_following_abstract+', 'BasePerson_following_abstract+',
                    'BasePerson_following_base+', 'BasePerson_following_base+', 'BasePerson_friends_abstract+',
                    'BasePerson_friends_abstract+', 'BasePerson_friends_base+', 'BasePerson_friends_base+',
                    'BasePerson_m2m_abstract+', 'BasePerson_m2m_base+', 'Relating_basepeople+',
                    'Relating_basepeople_hidden+', 'followers_abstract', 'followers_abstract', 'followers_abstract',
                    'followers_base', 'followers_base', 'followers_base', 'friends_abstract_rel_+', 'friends_abstract_rel_+',
                    'friends_abstract_rel_+', 'friends_base_rel_+', 'friends_base_rel_+', 'friends_base_rel_+', 'person',
                    'person', 'relating_basepeople', 'relating_baseperson'])
        )
        self.assertEqual([field.related_query_name() for field in AbstractPerson._meta._relation_tree], [])
