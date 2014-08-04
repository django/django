from django import test

from django.db.models import FieldDoesNotExist
from django.db.models.fields import related, CharField, Field
from django.db.models.options import IMMUTABLE_WARNING
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from .models import BasePerson, Person
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
        field_info = self._details(Person, Person._meta.get_field('m2m_base', m2m=True))
        self.assertEqual(field_info[1:], (BasePerson, True, True))
        self.assertIsInstance(field_info[0], related.ManyToManyField)

    def test_get_related_object(self):
        field_info = self._details(Person, Person._meta.get_field('relating_baseperson', related_objects=True))
        self.assertEqual(field_info[1:], (BasePerson, False, False))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_related_m2m(self):
        field_info = self._details(Person, Person._meta.get_field('relating_people', related_m2m=True))
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertIsInstance(field_info[0], related.RelatedObject)

    def test_get_generic_foreign_key(self):
        # For historic reasons generic foreign keys aren't available.
        with self.assertRaises(FieldDoesNotExist):
            Person._meta.get_field('content_object_base', virtual=True)

    def test_get_generic_relation(self):
        field_info = self._details(Person, Person._meta.get_field('generic_relation_base', virtual=True))
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericRelation)

    def test_get_m2m_field_invalid(self):
        self.assertRaises(
            FieldDoesNotExist,
            Person._meta.get_field,
            **{'field_name': 'm2m_base', 'm2m': False}
        )
