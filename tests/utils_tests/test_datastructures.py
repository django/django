"""
Tests for stuff in django.utils.datastructures.
"""

import copy
import pickle
import warnings

from django.test import SimpleTestCase
from django.utils.datastructures import (DictWrapper, ImmutableList,
    MultiValueDict, MultiValueDictKeyError, MergeDict, SortedDict)
from django.utils import six


class SortedDictTests(SimpleTestCase):
    def setUp(self):
        self.d1 = SortedDict()
        self.d1[7] = 'seven'
        self.d1[1] = 'one'
        self.d1[9] = 'nine'

        self.d2 = SortedDict()
        self.d2[1] = 'one'
        self.d2[9] = 'nine'
        self.d2[0] = 'nil'
        self.d2[7] = 'seven'

    def test_basic_methods(self):
        self.assertEqual(list(six.iterkeys(self.d1)), [7, 1, 9])
        self.assertEqual(list(six.itervalues(self.d1)), ['seven', 'one', 'nine'])
        self.assertEqual(list(six.iteritems(self.d1)), [(7, 'seven'), (1, 'one'), (9, 'nine')])

    def test_overwrite_ordering(self):
        """ Overwriting an item keeps its place. """
        self.d1[1] = 'ONE'
        self.assertEqual(list(six.itervalues(self.d1)), ['seven', 'ONE', 'nine'])

    def test_append_items(self):
        """ New items go to the end. """
        self.d1[0] = 'nil'
        self.assertEqual(list(six.iterkeys(self.d1)), [7, 1, 9, 0])

    def test_delete_and_insert(self):
        """
        Deleting an item, then inserting the same key again will place it
        at the end.
        """
        del self.d2[7]
        self.assertEqual(list(six.iterkeys(self.d2)), [1, 9, 0])
        self.d2[7] = 'lucky number 7'
        self.assertEqual(list(six.iterkeys(self.d2)), [1, 9, 0, 7])

    if six.PY2:
        def test_change_keys(self):
            """
            Changing the keys won't do anything, it's only a copy of the
            keys dict.

            This test doesn't make sense under Python 3 because keys is
            an iterator.
            """
            k = self.d2.keys()
            k.remove(9)
            self.assertEqual(self.d2.keys(), [1, 9, 0, 7])

    def test_init_keys(self):
        """
        Initialising a SortedDict with two keys will just take the first one.

        A real dict will actually take the second value so we will too, but
        we'll keep the ordering from the first key found.
        """
        tuples = ((2, 'two'), (1, 'one'), (2, 'second-two'))
        d = SortedDict(tuples)

        self.assertEqual(list(six.iterkeys(d)), [2, 1])

        real_dict = dict(tuples)
        self.assertEqual(sorted(six.itervalues(real_dict)), ['one', 'second-two'])

        # Here the order of SortedDict values *is* what we are testing
        self.assertEqual(list(six.itervalues(d)), ['second-two', 'one'])

    def test_overwrite(self):
        self.d1[1] = 'not one'
        self.assertEqual(self.d1[1], 'not one')
        self.assertEqual(list(six.iterkeys(self.d1)), list(six.iterkeys(self.d1.copy())))

    def test_append(self):
        self.d1[13] = 'thirteen'
        self.assertEqual(
            repr(self.d1),
            "{7: 'seven', 1: 'one', 9: 'nine', 13: 'thirteen'}"
        )

    def test_pop(self):
        self.assertEqual(self.d1.pop(1, 'missing'), 'one')
        self.assertEqual(self.d1.pop(1, 'missing'), 'missing')

        # We don't know which item will be popped in popitem(), so we'll
        # just check that the number of keys has decreased.
        l = len(self.d1)
        self.d1.popitem()
        self.assertEqual(l - len(self.d1), 1)

    def test_dict_equality(self):
        d = SortedDict((i, i) for i in range(3))
        self.assertEqual(d, {0: 0, 1: 1, 2: 2})

    def test_tuple_init(self):
        d = SortedDict(((1, "one"), (0, "zero"), (2, "two")))
        self.assertEqual(repr(d), "{1: 'one', 0: 'zero', 2: 'two'}")

    def test_pickle(self):
        self.assertEqual(
            pickle.loads(pickle.dumps(self.d1, 2)),
            {7: 'seven', 1: 'one', 9: 'nine'}
        )

    def test_copy(self):
        orig = SortedDict(((1, "one"), (0, "zero"), (2, "two")))
        copied = copy.copy(orig)
        self.assertEqual(list(six.iterkeys(orig)), [1, 0, 2])
        self.assertEqual(list(six.iterkeys(copied)), [1, 0, 2])

    def test_clear(self):
        self.d1.clear()
        self.assertEqual(self.d1, {})
        self.assertEqual(self.d1.keyOrder, [])

    def test_reversed(self):
        self.assertEqual(list(self.d1), [7, 1, 9])
        self.assertEqual(list(self.d2), [1, 9, 0, 7])
        self.assertEqual(list(reversed(self.d1)), [9, 1, 7])
        self.assertEqual(list(reversed(self.d2)), [7, 0, 9, 1])

    def test_insert(self):
        d = SortedDict()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            d.insert(0, "hello", "world")
        assert w[0].category is DeprecationWarning

    def test_value_for_index(self):
        d = SortedDict({"a": 3})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(d.value_for_index(0), 3)
        assert w[0].category is DeprecationWarning


class MergeDictTests(SimpleTestCase):

    def test_simple_mergedict(self):
        d1 = {'chris':'cool', 'camri':'cute', 'cotton':'adorable',
              'tulip':'snuggable', 'twoofme':'firstone'}

        d2 = {'chris2':'cool2', 'camri2':'cute2', 'cotton2':'adorable2',
              'tulip2':'snuggable2'}

        d3 = {'chris3':'cool3', 'camri3':'cute3', 'cotton3':'adorable3',
              'tulip3':'snuggable3'}

        d4 = {'twoofme': 'secondone'}

        md = MergeDict(d1, d2, d3)

        self.assertEqual(md['chris'], 'cool')
        self.assertEqual(md['camri'], 'cute')
        self.assertEqual(md['twoofme'], 'firstone')

        md2 = md.copy()
        self.assertEqual(md2['chris'], 'cool')

    def test_mergedict_merges_multivaluedict(self):
        """ MergeDict can merge MultiValueDicts """

        multi1 = MultiValueDict({'key1': ['value1'],
                                 'key2': ['value2', 'value3']})

        multi2 = MultiValueDict({'key2': ['value4'],
                                 'key4': ['value5', 'value6']})

        mm = MergeDict(multi1, multi2)

        # Although 'key2' appears in both dictionaries,
        # only the first value is used.
        self.assertEqual(mm.getlist('key2'), ['value2', 'value3'])
        self.assertEqual(mm.getlist('key4'), ['value5', 'value6'])
        self.assertEqual(mm.getlist('undefined'), [])

        self.assertEqual(sorted(six.iterkeys(mm)), ['key1', 'key2', 'key4'])
        self.assertEqual(len(list(six.itervalues(mm))), 3)

        self.assertTrue('value1' in six.itervalues(mm))

        self.assertEqual(sorted(six.iteritems(mm), key=lambda k: k[0]),
                          [('key1', 'value1'), ('key2', 'value3'),
                           ('key4', 'value6')])

        self.assertEqual([(k,mm.getlist(k)) for k in sorted(mm)],
                          [('key1', ['value1']),
                           ('key2', ['value2', 'value3']),
                           ('key4', ['value5', 'value6'])])

    def test_bool_casting(self):
        empty = MergeDict({}, {}, {})
        not_empty = MergeDict({}, {}, {"key": "value"})
        self.assertFalse(empty)
        self.assertTrue(not_empty)

    def test_key_error(self):
        """
        Test that the message of KeyError contains the missing key name.
        """
        d1 = MergeDict({'key1': 42})
        with six.assertRaisesRegex(self, KeyError, 'key2'):
            d1['key2']


class MultiValueDictTests(SimpleTestCase):

    def test_multivaluedict(self):
        d = MultiValueDict({'name': ['Adrian', 'Simon'],
                            'position': ['Developer']})

        self.assertEqual(d['name'], 'Simon')
        self.assertEqual(d.get('name'), 'Simon')
        self.assertEqual(d.getlist('name'), ['Adrian', 'Simon'])
        self.assertEqual(sorted(list(six.iteritems(d))),
                          [('name', 'Simon'), ('position', 'Developer')])

        self.assertEqual(sorted(list(six.iterlists(d))),
                          [('name', ['Adrian', 'Simon']),
                           ('position', ['Developer'])])

        six.assertRaisesRegex(self, MultiValueDictKeyError, 'lastname',
            d.__getitem__, 'lastname')

        self.assertEqual(d.get('lastname'), None)
        self.assertEqual(d.get('lastname', 'nonexistent'), 'nonexistent')
        self.assertEqual(d.getlist('lastname'), [])
        self.assertEqual(d.getlist('doesnotexist', ['Adrian', 'Simon']),
                         ['Adrian', 'Simon'])

        d.setlist('lastname', ['Holovaty', 'Willison'])
        self.assertEqual(d.getlist('lastname'), ['Holovaty', 'Willison'])
        self.assertEqual(sorted(list(six.itervalues(d))),
                         ['Developer', 'Simon', 'Willison'])

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
        self.assertEqual(sorted(six.iterkeys(d)), sorted(six.iterkeys(mvd)))
        for key in six.iterkeys(mvd):
            self.assertEqual(d[key], mvd[key])

        self.assertEqual({}, MultiValueDict().dict())


class ImmutableListTests(SimpleTestCase):

    def test_sort(self):
        d = ImmutableList(range(10))

        # AttributeError: ImmutableList object is immutable.
        self.assertRaisesMessage(AttributeError,
            'ImmutableList object is immutable.', d.sort)

        self.assertEqual(repr(d), '(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)')

    def test_custom_warning(self):
        d = ImmutableList(range(10), warning="Object is immutable!")

        self.assertEqual(d[1], 1)

        # AttributeError: Object is immutable!
        self.assertRaisesMessage(AttributeError,
            'Object is immutable!', d.__setitem__, 1, 'test')


class DictWrapperTests(SimpleTestCase):

    def test_dictwrapper(self):
        f = lambda x: "*%s" % x
        d = DictWrapper({'a': 'a'}, f, 'xx_')
        self.assertEqual("Normal: %(a)s. Modified: %(xx_a)s" % d,
                          'Normal: a. Modified: *a')
