from django.template.defaultfilters import dictsort
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

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
        Since dictsort uses template.Variable under the hood, it can sort
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
