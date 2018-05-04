"""
Tests for stuff in django.utils.datastructures.
"""

import copy

from django.test import SimpleTestCase
from django.utils.datastructures import (
    DictWrapper, ImmutableList, MultiValueDict, MultiValueDictKeyError,
    OrderedSet, ImmutableCaseInsensitiveDict
)


class OrderedSetTests(SimpleTestCase):

    def test_bool(self):
        # Refs #23664
        s = OrderedSet()
        self.assertFalse(s)
        s.add(1)
        self.assertTrue(s)

    def test_len(self):
        s = OrderedSet()
        self.assertEqual(len(s), 0)
        s.add(1)
        s.add(2)
        s.add(2)
        self.assertEqual(len(s), 2)


class MultiValueDictTests(SimpleTestCase):

    def test_multivaluedict(self):
        d = MultiValueDict({'name': ['Adrian', 'Simon'],
                            'position': ['Developer']})

        self.assertEqual(d['name'], 'Simon')
        self.assertEqual(d.get('name'), 'Simon')
        self.assertEqual(d.getlist('name'), ['Adrian', 'Simon'])
        self.assertEqual(
            sorted(d.items()),
            [('name', 'Simon'), ('position', 'Developer')]
        )

        self.assertEqual(
            sorted(d.lists()),
            [('name', ['Adrian', 'Simon']), ('position', ['Developer'])]
        )

        with self.assertRaises(MultiValueDictKeyError) as cm:
            d.__getitem__('lastname')
        self.assertEqual(str(cm.exception), "'lastname'")

        self.assertIsNone(d.get('lastname'))
        self.assertEqual(d.get('lastname', 'nonexistent'), 'nonexistent')
        self.assertEqual(d.getlist('lastname'), [])
        self.assertEqual(d.getlist('doesnotexist', ['Adrian', 'Simon']),
                         ['Adrian', 'Simon'])

        d.setlist('lastname', ['Holovaty', 'Willison'])
        self.assertEqual(d.getlist('lastname'), ['Holovaty', 'Willison'])
        self.assertEqual(sorted(d.values()), ['Developer', 'Simon', 'Willison'])

    def test_appendlist(self):
        d = MultiValueDict()
        d.appendlist('name', 'Adrian')
        d.appendlist('name', 'Simon')
        self.assertEqual(d.getlist('name'), ['Adrian', 'Simon'])

    def test_copy(self):
        for copy_func in [copy.copy, lambda d: d.copy()]:
            d1 = MultiValueDict({
                "developers": ["Carl", "Fred"]
            })
            self.assertEqual(d1["developers"], "Fred")
            d2 = copy_func(d1)
            d2.update({"developers": "Groucho"})
            self.assertEqual(d2["developers"], "Groucho")
            self.assertEqual(d1["developers"], "Fred")

            d1 = MultiValueDict({
                "key": [[]]
            })
            self.assertEqual(d1["key"], [])
            d2 = copy_func(d1)
            d2["key"].append("Penguin")
            self.assertEqual(d1["key"], ["Penguin"])
            self.assertEqual(d2["key"], ["Penguin"])

    def test_dict_translation(self):
        mvd = MultiValueDict({
            'devs': ['Bob', 'Joe'],
            'pm': ['Rory'],
        })
        d = mvd.dict()
        self.assertEqual(sorted(d), sorted(mvd))
        for key in mvd:
            self.assertEqual(d[key], mvd[key])

        self.assertEqual({}, MultiValueDict().dict())

    def test_getlist_doesnt_mutate(self):
        x = MultiValueDict({'a': ['1', '2'], 'b': ['3']})
        values = x.getlist('a')
        values += x.getlist('b')
        self.assertEqual(x.getlist('a'), ['1', '2'])

    def test_internal_getlist_does_mutate(self):
        x = MultiValueDict({'a': ['1', '2'], 'b': ['3']})
        values = x._getlist('a')
        values += x._getlist('b')
        self.assertEqual(x._getlist('a'), ['1', '2', '3'])

    def test_getlist_default(self):
        x = MultiValueDict({'a': [1]})
        MISSING = object()
        values = x.getlist('b', default=MISSING)
        self.assertIs(values, MISSING)

    def test_getlist_none_empty_values(self):
        x = MultiValueDict({'a': None, 'b': []})
        self.assertIsNone(x.getlist('a'))
        self.assertEqual(x.getlist('b'), [])


class ImmutableListTests(SimpleTestCase):

    def test_sort(self):
        d = ImmutableList(range(10))

        # AttributeError: ImmutableList object is immutable.
        with self.assertRaisesMessage(AttributeError, 'ImmutableList object is immutable.'):
            d.sort()

        self.assertEqual(repr(d), '(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)')

    def test_custom_warning(self):
        d = ImmutableList(range(10), warning="Object is immutable!")

        self.assertEqual(d[1], 1)

        # AttributeError: Object is immutable!
        with self.assertRaisesMessage(AttributeError, 'Object is immutable!'):
            d.__setitem__(1, 'test')


class DictWrapperTests(SimpleTestCase):

    def test_dictwrapper(self):
        def f(x):
            return "*%s" % x
        d = DictWrapper({'a': 'a'}, f, 'xx_')
        self.assertEqual(
            "Normal: %(a)s. Modified: %(xx_a)s" % d,
            'Normal: a. Modified: *a'
        )


class ImmutableCaseInsensitiveDictTests(SimpleTestCase):
    def setUp(self):
        self.dict_1 = ImmutableCaseInsensitiveDict({
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

    def test_list(self):
        self.assertEqual(
            sorted(list(self.dict_1)),
            sorted(['Accept', 'content-type']))

    def test_dict(self):
        self.assertEqual(dict(self.dict_1), {
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

    def test_repr(self):
        self.assertEqual(repr(self.dict_1), repr({
            'Accept': 'application/json',
            'content-type': 'text/html'
        }))

    def test_str(self):
        self.assertEqual(str(self.dict_1), str({
            'Accept': 'application/json',
            'content-type': 'text/html'
        }))

    def test_equals(self):
        self.assertTrue(self.dict_1 == {
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

        self.assertTrue(self.dict_1 == {
            'accept': 'application/json',
            'Content-Type': 'text/html'
        })

    def test_items(self):
        other = {
            'Accept': 'application/json',
            'content-type': 'text/html'
        }
        self.assertEqual(list(self.dict_1.items()), list(other.items()))

    def test_copy(self):
        copy = self.dict_1.copy()

        # id(copy) != id(self.dict_1)
        self.assertIsNot(copy, self.dict_1)
        self.assertEqual(copy, self.dict_1)

    def test_getitem(self):
        self.assertEqual(self.dict_1['Accept'], 'application/json')
        self.assertEqual(self.dict_1['accept'], 'application/json')
        self.assertEqual(self.dict_1['aCCept'], 'application/json')

        self.assertEqual(self.dict_1['content-type'], 'text/html')
        self.assertEqual(self.dict_1['Content-Type'], 'text/html')
        self.assertEqual(self.dict_1['Content-type'], 'text/html')

    def test_membership(self):
        self.assertTrue('Accept' in self.dict_1)
        self.assertTrue('accept' in self.dict_1)
        self.assertTrue('aCCept' in self.dict_1)

        self.assertTrue('content-type' in self.dict_1)
        self.assertTrue('Content-Type' in self.dict_1)

    def test_delitem(self):
        "del should raise a TypeError because this is immutable"
        # Preconditions
        self.assertTrue('Accept' in self.dict_1)
        with self.assertRaises(TypeError):
            del self.dict_1['Accept']

        # Postconditions
        self.assertTrue('Accept' in self.dict_1)

    def test_setitem(self):
        "del should raise a TypeError because this is immutable"
        # Preconditions
        self.assertEqual(len(self.dict_1), 2)

        with self.assertRaises(TypeError):
            self.dict_1['New Key'] = 1

        # Postconditions
        self.assertEqual(len(self.dict_1), 2)
