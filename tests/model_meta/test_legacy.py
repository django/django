import warnings

from django import test
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields import CharField, related
from django.utils.deprecation import RemovedInDjango110Warning

from .models import BasePerson, Person
from .results import TEST_RESULTS


class OptionsBaseTests(test.SimpleTestCase):

    def _map_related_query_names(self, res):
        return tuple((o.field.related_query_name(), m) for o, m in res)

    def _map_names(self, res):
        return tuple((f.name, m) for f, m in res)


class M2MTests(OptionsBaseTests):

    def test_many_to_many_with_model(self):
        for model, expected_result in TEST_RESULTS['many_to_many_with_model'].items():
            with warnings.catch_warnings(record=True) as warning:
                warnings.simplefilter("always")
                models = [model for field, model in model._meta.get_m2m_with_model()]
                self.assertEqual([RemovedInDjango110Warning], [w.message.__class__ for w in warning])
            self.assertEqual(models, expected_result)


@test.ignore_warnings(category=RemovedInDjango110Warning)
class RelatedObjectsTests(OptionsBaseTests):
    key_name = lambda self, r: r[0]

    def test_related_objects(self):
        result_key = 'get_all_related_objects_with_model_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model()
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_local(self):
        result_key = 'get_all_related_objects_with_model_local_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(local_only=True)
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_include_hidden(self):
        result_key = 'get_all_related_objects_with_model_hidden_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(include_hidden=True)
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )

    def test_related_objects_include_hidden_local_only(self):
        result_key = 'get_all_related_objects_with_model_hidden_local_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_hidden=True, local_only=True)
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )

    def test_related_objects_proxy(self):
        result_key = 'get_all_related_objects_with_model_proxy_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True)
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_objects_proxy_hidden(self):
        result_key = 'get_all_related_objects_with_model_proxy_hidden_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_objects_with_model(
                include_proxy_eq=True, include_hidden=True)
            self.assertEqual(
                sorted(self._map_names(objects), key=self.key_name),
                sorted(expected, key=self.key_name)
            )


@test.ignore_warnings(category=RemovedInDjango110Warning)
class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        result_key = 'get_all_related_many_to_many_with_model_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_m2m_objects_with_model()
            self.assertEqual(self._map_related_query_names(objects), expected)

    def test_related_m2m_local_only(self):
        result_key = 'get_all_related_many_to_many_local_legacy'
        for model, expected in TEST_RESULTS[result_key].items():
            objects = model._meta.get_all_related_many_to_many_objects(local_only=True)
            self.assertEqual([o.field.related_query_name() for o in objects], expected)

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


@test.ignore_warnings(category=RemovedInDjango110Warning)
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
        self.assertTrue(field_info[0].auto_created)

    def test_get_related_m2m(self):
        field_info = Person._meta.get_field_by_name('relating_people')
        self.assertEqual(field_info[1:], (None, False, True))
        self.assertTrue(field_info[0].auto_created)

    def test_get_generic_relation(self):
        field_info = Person._meta.get_field_by_name('generic_relation_base')
        self.assertEqual(field_info[1:], (None, True, False))
        self.assertIsInstance(field_info[0], GenericRelation)

    def test_get_m2m_field_invalid(self):
        with warnings.catch_warnings(record=True) as warning:
            warnings.simplefilter("always")
            self.assertRaises(
                FieldDoesNotExist,
                Person._meta.get_field,
                **{'field_name': 'm2m_base', 'many_to_many': False}
            )
            self.assertEqual(Person._meta.get_field('m2m_base', many_to_many=True).name, 'm2m_base')

            # 2 RemovedInDjango110Warning messages should be raised, one for each call of get_field()
            # with the 'many_to_many' argument.
            self.assertEqual(
                [RemovedInDjango110Warning, RemovedInDjango110Warning],
                [w.message.__class__ for w in warning]
            )


@test.ignore_warnings(category=RemovedInDjango110Warning)
class GetAllFieldNamesTestCase(OptionsBaseTests):

    def test_get_all_field_names(self):
        for model, expected_names in TEST_RESULTS['get_all_field_names'].items():
            objects = model._meta.get_all_field_names()
            self.assertEqual(sorted(map(str, objects)), sorted(expected_names))
