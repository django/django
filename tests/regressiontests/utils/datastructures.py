"""
Tests for stuff in django.utils.datastructures.
"""
import pickle
import unittest

from django.utils.datastructures import *


class DatastructuresTestCase(unittest.TestCase):
    def assertRaisesErrorWithMessage(self, error, message, callable,
        *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))


class SortedDictTests(DatastructuresTestCase):
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
        self.assertEquals(self.d1.keys(), [7, 1, 9])
        self.assertEquals(self.d1.values(), ['seven', 'one', 'nine'])
        self.assertEquals(self.d1.items(), [(7, 'seven'), (1, 'one'), (9, 'nine')])

    def test_overwrite_ordering(self):
        """ Overwriting an item keeps it's place. """
        self.d1[1] = 'ONE'
        self.assertEquals(self.d1.values(), ['seven', 'ONE', 'nine'])

    def test_append_items(self):
        """ New items go to the end. """
        self.d1[0] = 'nil'
        self.assertEquals(self.d1.keys(), [7, 1, 9, 0])

    def test_delete_and_insert(self):
        """
        Deleting an item, then inserting the same key again will place it
        at the end.
        """
        del self.d2[7]
        self.assertEquals(self.d2.keys(), [1, 9, 0])
        self.d2[7] = 'lucky number 7'
        self.assertEquals(self.d2.keys(), [1, 9, 0, 7])

    def test_change_keys(self):
        """
        Changing the keys won't do anything, it's only a copy of the
        keys dict.
        """
        k = self.d2.keys()
        k.remove(9)
        self.assertEquals(self.d2.keys(), [1, 9, 0, 7])

    def test_init_keys(self):
        """
        Initialising a SortedDict with two keys will just take the first one.

        A real dict will actually take the second value so we will too, but
        we'll keep the ordering from the first key found.
        """
        tuples = ((2, 'two'), (1, 'one'), (2, 'second-two'))
        d = SortedDict(tuples)

        self.assertEquals(d.keys(), [2, 1])

        real_dict = dict(tuples)
        self.assertEquals(sorted(real_dict.values()), ['one', 'second-two'])

        # Here the order of SortedDict values *is* what we are testing
        self.assertEquals(d.values(), ['second-two', 'one'])

    def test_overwrite(self):
        self.d1[1] = 'not one'
        self.assertEqual(self.d1[1], 'not one')
        self.assertEqual(self.d1.keys(), self.d1.copy().keys())

    def test_append(self):
        self.d1[13] = 'thirteen'
        self.assertEquals(
            repr(self.d1),
            "{7: 'seven', 1: 'one', 9: 'nine', 13: 'thirteen'}"
        )

    def test_pop(self):
        self.assertEquals(self.d1.pop(1, 'missing'), 'one')
        self.assertEquals(self.d1.pop(1, 'missing'), 'missing')

        # We don't know which item will be popped in popitem(), so we'll
        # just check that the number of keys has decreased.
        l = len(self.d1)
        self.d1.popitem()
        self.assertEquals(l - len(self.d1), 1)

    def test_dict_equality(self):
        d = SortedDict((i, i) for i in xrange(3))
        self.assertEquals(d, {0: 0, 1: 1, 2: 2})

    def test_tuple_init(self):
        d = SortedDict(((1, "one"), (0, "zero"), (2, "two")))
        self.assertEquals(repr(d), "{1: 'one', 0: 'zero', 2: 'two'}")

    def test_pickle(self):
        self.assertEquals(
            pickle.loads(pickle.dumps(self.d1, 2)),
            {7: 'seven', 1: 'one', 9: 'nine'}
        )

    def test_clear(self):
        self.d1.clear()
        self.assertEquals(self.d1, {})
        self.assertEquals(self.d1.keyOrder, [])

class MergeDictTests(DatastructuresTestCase):

    def test_simple_mergedict(self):
        d1 = {'chris':'cool', 'camri':'cute', 'cotton':'adorable',
              'tulip':'snuggable', 'twoofme':'firstone'}

        d2 = {'chris2':'cool2', 'camri2':'cute2', 'cotton2':'adorable2',
              'tulip2':'snuggable2'}

        d3 = {'chris3':'cool3', 'camri3':'cute3', 'cotton3':'adorable3',
              'tulip3':'snuggable3'}

        d4 = {'twoofme': 'secondone'}

        md = MergeDict(d1, d2, d3)

        self.assertEquals(md['chris'], 'cool')
        self.assertEquals(md['camri'], 'cute')
        self.assertEquals(md['twoofme'], 'firstone')

        md2 = md.copy()
        self.assertEquals(md2['chris'], 'cool')

    def test_mergedict_merges_multivaluedict(self):
        """ MergeDict can merge MultiValueDicts """

        multi1 = MultiValueDict({'key1': ['value1'],
                                 'key2': ['value2', 'value3']})

        multi2 = MultiValueDict({'key2': ['value4'],
                                 'key4': ['value5', 'value6']})

        mm = MergeDict(multi1, multi2)

        # Although 'key2' appears in both dictionaries,
        # only the first value is used.
        self.assertEquals(mm.getlist('key2'), ['value2', 'value3'])
        self.assertEquals(mm.getlist('key4'), ['value5', 'value6'])
        self.assertEquals(mm.getlist('undefined'), [])

        self.assertEquals(sorted(mm.keys()), ['key1', 'key2', 'key4'])
        self.assertEquals(len(mm.values()), 3)

        self.assertTrue('value1' in mm.values())

        self.assertEquals(sorted(mm.items(), key=lambda k: k[0]),
                          [('key1', 'value1'), ('key2', 'value3'),
                           ('key4', 'value6')])

        self.assertEquals([(k,mm.getlist(k)) for k in sorted(mm)],
                          [('key1', ['value1']),
                           ('key2', ['value2', 'value3']),
                           ('key4', ['value5', 'value6'])])

class MultiValueDictTests(DatastructuresTestCase):

    def test_multivaluedict(self):
        d = MultiValueDict({'name': ['Adrian', 'Simon'],
                            'position': ['Developer']})

        self.assertEquals(d['name'], 'Simon')
        self.assertEquals(d.get('name'), 'Simon')
        self.assertEquals(d.getlist('name'), ['Adrian', 'Simon'])
        self.assertEquals(list(d.iteritems()),
                          [('position', 'Developer'), ('name', 'Simon')])

        self.assertEquals(list(d.iterlists()),
                          [('position', ['Developer']),
                           ('name', ['Adrian', 'Simon'])])

        # MultiValueDictKeyError: "Key 'lastname' not found in
        # <MultiValueDict: {'position': ['Developer'],
        #                   'name': ['Adrian', 'Simon']}>"
        self.assertRaisesErrorWithMessage(MultiValueDictKeyError,
            '"Key \'lastname\' not found in <MultiValueDict: {\'position\':'\
            ' [\'Developer\'], \'name\': [\'Adrian\', \'Simon\']}>"',
            d.__getitem__, 'lastname')

        self.assertEquals(d.get('lastname'), None)
        self.assertEquals(d.get('lastname', 'nonexistent'), 'nonexistent')
        self.assertEquals(d.getlist('lastname'), [])

        d.setlist('lastname', ['Holovaty', 'Willison'])
        self.assertEquals(d.getlist('lastname'), ['Holovaty', 'Willison'])
        self.assertEquals(d.values(), ['Developer', 'Simon', 'Willison'])
        self.assertEquals(list(d.itervalues()),
                          ['Developer', 'Simon', 'Willison'])


class DotExpandedDictTests(DatastructuresTestCase):

    def test_dotexpandeddict(self):

        d = DotExpandedDict({'person.1.firstname': ['Simon'],
                             'person.1.lastname': ['Willison'],
                             'person.2.firstname': ['Adrian'],
                             'person.2.lastname': ['Holovaty']})

        self.assertEquals(d['person']['1']['lastname'], ['Willison'])
        self.assertEquals(d['person']['2']['lastname'], ['Holovaty'])
        self.assertEquals(d['person']['2']['firstname'], ['Adrian'])


class ImmutableListTests(DatastructuresTestCase):

    def test_sort(self):
        d = ImmutableList(range(10))

        # AttributeError: ImmutableList object is immutable.
        self.assertRaisesErrorWithMessage(AttributeError,
            'ImmutableList object is immutable.', d.sort)

        self.assertEquals(repr(d), '(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)')

    def test_custom_warning(self):
        d = ImmutableList(range(10), warning="Object is immutable!")

        self.assertEquals(d[1], 1)

        # AttributeError: Object is immutable!
        self.assertRaisesErrorWithMessage(AttributeError,
            'Object is immutable!', d.__setitem__, 1, 'test')


class DictWrapperTests(DatastructuresTestCase):

    def test_dictwrapper(self):
        f = lambda x: "*%s" % x
        d = DictWrapper({'a': 'a'}, f, 'xx_')
        self.assertEquals("Normal: %(a)s. Modified: %(xx_a)s" % d,
                          'Normal: a. Modified: *a')
