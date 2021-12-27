from django.template.defaultfilters import _property_resolver, dictsort
from django.test import SimpleTestCase


class User:
    password = 'abc'

    _private = 'private'

    @property
    def test_property(self):
        return 'cde'

    def test_method(self):
        """This is just a test method."""


class FunctionTests(SimpleTestCase):

    def test_property_resolver(self):
        user = User()
        dict_data = {'a': {
            'b1': {'c': 'result1'},
            'b2': user,
            'b3': {'0': 'result2'},
            'b4': [0, 1, 2],
        }}
        list_data = ['a', 'b', 'c']
        tests = [
            ('a.b1.c', dict_data, 'result1'),
            ('a.b2.password', dict_data, 'abc'),
            ('a.b2.test_property', dict_data, 'cde'),
            # The method should not get called.
            ('a.b2.test_method', dict_data, user.test_method),
            ('a.b3.0', dict_data, 'result2'),
            (0, list_data, 'a'),
        ]
        for arg, data, expected_value in tests:
            with self.subTest(arg=arg):
                self.assertEqual(_property_resolver(arg)(data), expected_value)
        # Invalid lookups.
        fail_tests = [
            ('a.b1.d', dict_data, AttributeError),
            ('a.b2.password.0', dict_data, AttributeError),
            ('a.b2._private', dict_data, AttributeError),
            ('a.b4.0', dict_data, AttributeError),
            ('a', list_data, AttributeError),
            ('0', list_data, TypeError),
            (4, list_data, IndexError),
        ]
        for arg, data, expected_exception in fail_tests:
            with self.subTest(arg=arg):
                with self.assertRaises(expected_exception):
                    _property_resolver(arg)(data)

    def test_sort(self):
        sorted_dicts = dictsort(
            [{'age': 23, 'name': 'Barbara-Ann'},
             {'age': 63, 'name': 'Ra Ra Rasputin'},
             {'name': 'Jonny B Goode', 'age': 18}],
            'age',
        )

        self.assertEqual(
            [sorted(dict.items()) for dict in sorted_dicts],
            [[('age', 18), ('name', 'Jonny B Goode')],
             [('age', 23), ('name', 'Barbara-Ann')],
             [('age', 63), ('name', 'Ra Ra Rasputin')]],
        )

    def test_dictsort_complex_sorting_key(self):
        """
        Since dictsort uses dict.get()/getattr() under the hood, it can sort
        on keys like 'foo.bar'.
        """
        data = [
            {'foo': {'bar': 1, 'baz': 'c'}},
            {'foo': {'bar': 2, 'baz': 'b'}},
            {'foo': {'bar': 3, 'baz': 'a'}},
        ]
        sorted_data = dictsort(data, 'foo.baz')

        self.assertEqual([d['foo']['bar'] for d in sorted_data], [3, 2, 1])

    def test_sort_list_of_tuples(self):
        data = [('a', '42'), ('c', 'string'), ('b', 'foo')]
        expected = [('a', '42'), ('b', 'foo'), ('c', 'string')]
        self.assertEqual(dictsort(data, 0), expected)

    def test_sort_list_of_tuple_like_dicts(self):
        data = [
            {'0': 'a', '1': '42'},
            {'0': 'c', '1': 'string'},
            {'0': 'b', '1': 'foo'},
        ]
        expected = [
            {'0': 'a', '1': '42'},
            {'0': 'b', '1': 'foo'},
            {'0': 'c', '1': 'string'},
        ]
        self.assertEqual(dictsort(data, '0'), expected)

    def test_invalid_values(self):
        """
        If dictsort is passed something other than a list of dictionaries,
        fail silently.
        """
        self.assertEqual(dictsort([1, 2, 3], 'age'), '')
        self.assertEqual(dictsort('Hello!', 'age'), '')
        self.assertEqual(dictsort({'a': 1}, 'age'), '')
        self.assertEqual(dictsort(1, 'age'), '')

    def test_invalid_args(self):
        """Fail silently if invalid lookups are passed."""
        self.assertEqual(dictsort([{}], '._private'), '')
        self.assertEqual(dictsort([{'_private': 'test'}], '_private'), '')
        self.assertEqual(dictsort([{'nested': {'_private': 'test'}}], 'nested._private'), '')
