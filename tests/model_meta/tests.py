from django.apps import apps
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields import CharField, Field, related
from django.db.models.options import EMPTY_RELATION_TREE, IMMUTABLE_WARNING
from django.test import SimpleTestCase

from .models import (
    AbstractPerson, BasePerson, Child, CommonAncestor, FirstParent, Person,
    ProxyPerson, Relating, Relation, SecondParent,
)
from .results import TEST_RESULTS


class OptionsBaseTests(SimpleTestCase):

    def _map_related_query_names(self, res):
        return tuple((o.name, m) for o, m in res)

    def _map_names(self, res):
        return tuple((f.name, m) for f, m in res)

    def _model(self, current_model, field):
        model = field.model._meta.concrete_model
        return None if model == current_model else model

    def _details(self, current_model, relation):
        direct = isinstance(relation, (Field, GenericForeignKey))
        model = relation.model._meta.concrete_model
        if model == current_model:
            model = None

        field = relation if direct else relation.field
        return relation, model, direct, bool(field.many_to_many)  # many_to_many can be None


class GetFieldsTests(OptionsBaseTests):

    def test_get_fields_is_immutable(self):
        msg = IMMUTABLE_WARNING % "get_fields()"
        for _ in range(2):
            # Running unit test twice to ensure both non-cached and cached result
            # are immutable.
            fields = Person._meta.get_fields()
            with self.assertRaisesMessage(AttributeError, msg):
                fields += ["errors"]


class LabelTests(OptionsBaseTests):

    def test_label(self):
        for model, expected_result in TEST_RESULTS['labels'].items():
            self.assertEqual(model._meta.label, expected_result)

    def test_label_lower(self):
        for model, expected_result in TEST_RESULTS['lower_labels'].items():
            self.assertEqual(model._meta.label_lower, expected_result)


class DataTests(OptionsBaseTests):

    def test_fields(self):
        for model, expected_result in TEST_RESULTS['fields'].items():
            fields = model._meta.fields
            self.assertEqual([f.attname for f in fields], expected_result)

    def test_local_fields(self):
        def is_data_field(f):
            return isinstance(f, Field) and not f.many_to_many

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
                self.assertIsNotNone(f.column)


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        for model, expected_result in TEST_RESULTS['many_to_many'].items():
            fields = model._meta.many_to_many
            self.assertEqual([f.attname for f in fields], expected_result)
            for f in fields:
                self.assertTrue(f.many_to_many and f.is_relation)

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            models = [self._model(model, field) for field in model._meta.many_to_many]
            self.assertEqual(models, expected_result)


class RelatedObjectsTests(OptionsBaseTests):
    def key_name(self, r):
        return r[0]

    def test_related_objects(self):
        result_key = 'get_all_related_objects_with_model'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields()
                if field.auto_created and not field.concrete
            ]
            self.assertEqual(
                sorted(self._map_related_query_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name),
            )

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(include_parents=False)
                if field.auto_created and not field.concrete
            ]
            self.assertEqual(
                sorted(self._map_related_query_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name),
            )

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = [
                (field, self._model(model, field))
                for field in model._meta.get_fields(include_hidden=True)
                if field.auto_created and not field.concrete
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
                if field.auto_created and not field.concrete
            ]
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )


class PrivateFieldsTests(OptionsBaseTests):

    def test_private_fields(self):
        for model, expected_names in TEST_RESULTS['private_fields'].items():
            objects = model._meta.private_fields
            self.assertEqual(sorted(f.name for f in objects), sorted(expected_names))


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
        self.assertIsInstance(field_info[0], related.ForeignObjectRel)

    def test_get_related_m2m(self):
        field_info = self._details(Person, Person._meta.get_field('relating_people'))
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertIsInstance(field_info[0], related.ForeignObjectRel)

    def test_get_generic_relation(self):
        field_info = self._details(Person, Person._meta.get_field('generic_relation_base'))
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericRelation)

    def test_get_fields_only_searches_forward_on_apps_not_ready(self):
        opts = Person._meta
        # If apps registry is not ready, get_field() searches over only
        # forward fields.
        opts.apps.models_ready = False
        try:
            # 'data_abstract' is a forward field, and therefore will be found
            self.assertTrue(opts.get_field('data_abstract'))
            msg = (
                "Person has no field named 'relating_baseperson'. The app "
                "cache isn't ready yet, so if this is an auto-created related "
                "field, it won't be available yet."
            )
            # 'data_abstract' is a reverse field, and will raise an exception
            with self.assertRaisesMessage(FieldDoesNotExist, msg):
                opts.get_field('relating_baseperson')
        finally:
            opts.apps.models_ready = True


class RelationTreeTests(SimpleTestCase):
    all_models = (Relation, AbstractPerson, BasePerson, Person, ProxyPerson, Relating)

    def setUp(self):
        apps.clear_cache()

    def test_clear_cache_clears_relation_tree(self):
        # The apps.clear_cache is setUp() should have deleted all trees.
        # Exclude abstract models that are not included in the Apps registry
        # and have no cache.
        all_models_with_cache = (m for m in self.all_models if not m._meta.abstract)
        for m in all_models_with_cache:
            self.assertNotIn('_relation_tree', m._meta.__dict__)

    def test_first_relation_tree_access_populates_all(self):
        # On first access, relation tree should have populated cache.
        self.assertTrue(self.all_models[0]._meta._relation_tree)

        # AbstractPerson does not have any relations, so relation_tree
        # should just return an EMPTY_RELATION_TREE.
        self.assertEqual(AbstractPerson._meta._relation_tree, EMPTY_RELATION_TREE)

        # All the other models should already have their relation tree
        # in the internal __dict__ .
        all_models_but_abstractperson = (m for m in self.all_models if m is not AbstractPerson)
        for m in all_models_but_abstractperson:
            self.assertIn('_relation_tree', m._meta.__dict__)

    def test_relations_related_objects(self):
        # Testing non hidden related objects
        self.assertEqual(
            sorted(field.related_query_name() for field in Relation._meta._relation_tree
                   if not field.remote_field.field.remote_field.is_hidden()),
            sorted([
                'fk_abstract_rel', 'fk_base_rel', 'fk_concrete_rel', 'fo_abstract_rel',
                'fo_base_rel', 'fo_concrete_rel', 'm2m_abstract_rel',
                'm2m_base_rel', 'm2m_concrete_rel'
            ])
        )
        # Testing hidden related objects
        self.assertEqual(
            sorted(field.related_query_name() for field in BasePerson._meta._relation_tree),
            sorted([
                '+', '_relating_basepeople_hidden_+', 'BasePerson_following_abstract+',
                'BasePerson_following_abstract+', 'BasePerson_following_base+', 'BasePerson_following_base+',
                'BasePerson_friends_abstract+', 'BasePerson_friends_abstract+', 'BasePerson_friends_base+',
                'BasePerson_friends_base+', 'BasePerson_m2m_abstract+', 'BasePerson_m2m_base+', 'Relating_basepeople+',
                'Relating_basepeople_hidden+', 'followers_abstract', 'followers_base', 'friends_abstract_rel_+',
                'friends_base_rel_+', 'person', 'relating_basepeople', 'relating_baseperson',
            ])
        )
        self.assertEqual([field.related_query_name() for field in AbstractPerson._meta._relation_tree], [])


class ParentListTests(SimpleTestCase):
    def test_get_parent_list(self):
        self.assertEqual(CommonAncestor._meta.get_parent_list(), [])
        self.assertEqual(FirstParent._meta.get_parent_list(), [CommonAncestor])
        self.assertEqual(SecondParent._meta.get_parent_list(), [CommonAncestor])
        self.assertEqual(Child._meta.get_parent_list(), [FirstParent, SecondParent, CommonAncestor])


class PropertyNamesTests(SimpleTestCase):
    def test_person(self):
        # Instance only descriptors don't appear in _property_names.
        self.assertEqual(AbstractPerson().test_instance_only_descriptor, 1)
        self.assertEqual(AbstractPerson._meta._property_names, frozenset(['pk', 'test_property']))


class ReturningFieldsTests(SimpleTestCase):
    def test_pk(self):
        self.assertEqual(Relation._meta.db_returning_fields, [Relation._meta.pk])
