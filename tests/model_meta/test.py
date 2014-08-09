from django import test

from django.apps import apps
from django.db.models import FieldDoesNotExist
from django.db.models.fields import related, CharField, Field
from django.db.models.options import IMMUTABLE_WARNING, EMPTY_RELATION_TREE
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

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


class DataTests(OptionsBaseTests):

    def test_fields(self):
        for model, expected_result in TEST_RESULTS['fields'].items():
            fields = model._meta.get_fields()
            self.assertEqual([f.attname for f in fields], expected_result)

    def test_local_fields(self):
        is_data_field = lambda f: isinstance(f, Field) and not isinstance(f, related.ManyToManyField)

        for model, expected_result in TEST_RESULTS['local_fields'].items():
            fields = model._meta.get_fields(include_parents=False)
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([f.model is model for f in fields]))
            self.assertTrue(all([is_data_field(f) for f in fields]))

    def test_local_concrete_fields(self):
        for model, expected_result in TEST_RESULTS['local_concrete_fields'].items():
            fields = model._meta.local_concrete_fields
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([f.column is not None for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        for model, expected_result in TEST_RESULTS['many_to_many'].items():
            fields = model._meta.get_fields(data=False, m2m=True)
            self.assertEqual([f.attname for f in fields], expected_result)
            self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                                 for f in fields]))

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            models = [self._model(model, field) for field in model._meta.get_fields(data=False, m2m=True)]
            self.assertEqual(models, expected_result)


class RelatedObjectsTests(OptionsBaseTests):
    def setUp(self):
        self.key_name = lambda r: r[0]

    def test_related_objects(self):
        result_key = 'get_all_related_objects_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [(field, self._model(model, field))
                       for field in model._meta.get_fields(data=False, related_objects=True)]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [(field, self._model(model, field))
                       for field in model._meta.get_fields(data=False, related_objects=True, include_parents=False)]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [(field, self._model(model, field))
                       for field in model._meta.get_fields(data=False, related_objects=True, include_hidden=True)]
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )

    def test_related_objects_include_hidden_local_only(self):
        result_key = 'get_all_related_objects_with_model_hidden_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [(field, self._model(model, field))
                       for field in model._meta.get_fields(data=False, related_objects=True, include_hidden=True, include_parents=False)]
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        result_key = 'get_all_related_many_to_many_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [(field, self._model(model, field))
                       for field in model._meta.get_fields(data=False, related_m2m=True)]
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_m2m_local_only(self):
        result_key = 'get_all_related_many_to_many_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_fields(data=False, related_m2m=True, include_parents=False)
            self.assertEqual([o.field.related_query_name()
                              for o in objects], expected)

    def test_related_m2m_asymmetrical(self):
        m2m = Person._meta.get_fields(data=False, m2m=True)
        self.assertTrue('following_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_fields(data=False, related_m2m=True)
        self.assertTrue('followers_base' in [o.field.related_query_name() for o in related_m2m])

    def test_related_m2m_symmetrical(self):
        m2m = Person._meta.get_fields(data=False, m2m=True)
        self.assertTrue('friends_base' in [f.attname for f in m2m])
        related_m2m = Person._meta.get_fields(data=False, related_m2m=True)
        self.assertIn('friends_inherited_rel_+', [o.field.related_query_name() for o in related_m2m])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        for model, expected_names in TEST_RESULTS['virtual_fields'].items():
            objects = model._meta.get_fields(data=False, virtual=True)
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
        self.assertTrue(all('relation_tree' not in m._meta.__dict__
                            for m in self.all_models))

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
        all_models_but_abstractperson = (m for m in self.all_models
                                         if m is not AbstractPerson)
        self.assertTrue(all('relation_tree' in m._meta.__dict__
                            for m in all_models_but_abstractperson))

    def test_relations_related_objects(self):

        # Testing non hidden related objects
        self.assertEqual(
            sorted([field.related_query_name() for field in Relation._meta.relation_tree.related_objects
                   if not field.related.field.rel.is_hidden()]),
            sorted(['fk_abstract_rel', 'fo_abstract_rel', 'fk_base_rel', 'fo_base_rel', 'fk_abstract_rel',
                   'fo_abstract_rel', 'fk_base_rel', 'fo_base_rel', 'fk_concrete_rel', 'fo_concrete_rel',
                   'fk_abstract_rel', 'fo_abstract_rel', 'fk_base_rel', 'fo_base_rel', 'fk_concrete_rel',
                   'fo_concrete_rel'])
        )

        # Testing hidden related objects
        self.assertEqual(
            sorted([field.related_query_name() for field in BasePerson._meta.relation_tree.related_objects]),
            sorted(['BasePerson_friends_base+', 'BasePerson_friends_base+', 'BasePerson_m2m_base+',
                   'BasePerson_following_base+', 'BasePerson_following_base+', 'BasePerson_m2m_abstract+',
                   'BasePerson_friends_abstract+', 'BasePerson_friends_abstract+', 'BasePerson_following_abstract+',
                   'BasePerson_following_abstract+', 'person', 'person', 'Relating_basepeople+', 'Relating_basepeople_hidden+',
                   'relating_baseperson', '+'])
        )
        self.assertEqual([field.related_query_name() for field in AbstractPerson._meta.relation_tree.related_objects], [])

    def test_relations_related_m2m(self):
        self.assertEqual(
            sorted([field.related_query_name() for field in Relation._meta.relation_tree.related_m2m
                   if not field.related.field.rel.is_hidden()]),
            sorted(['m2m_abstract_rel', 'm2m_base_rel', 'm2m_abstract_rel', 'm2m_base_rel', 'm2m_concrete_rel',
                   'm2m_abstract_rel', 'm2m_base_rel', 'm2m_concrete_rel'])
        )
        self.assertEqual([field.related_query_name() for field in AbstractPerson._meta.relation_tree.related_m2m], [])
