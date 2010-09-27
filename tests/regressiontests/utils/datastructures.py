from django.test import TestCase
from django.utils.datastructures import SortedDict

class DatastructuresTests(TestCase):
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
