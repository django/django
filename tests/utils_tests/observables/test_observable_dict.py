from django.test import TestCase
from django.utils.observables import ChangeRecord, ObservableDict


class Observer(object):
    def __init__(self):
        self.changes = list()

    def handle_changes(self, change_records):
        self.changes = list(change_records)


class TestObservableDict(TestCase):
    def setUp(self):
        self.observer = Observer()
        self._mkdict()

    def _mkdict(self):
        self.observer.changes.clear()
        self.dict = ObservableDict({
            'a': 1,
            'b': 2,
            'c': 3
        })
        self.dict.add_observer(self.observer)

    def assertItemsEqual(self, iterable1, iterable2):
        self.assert_(sorted(iterable1) == sorted(iterable2))

    def test_delitem(self):
        del self.dict['a']
        self.assertEquals(self.dict, {'b': 2, 'c': 3})
        self.assertEquals(self.observer.changes, [
            ChangeRecord.item(self.dict, 'a', old=1)
        ])

    def test_setitem(self):
        self.dict['a'] = 26
        self.assertEquals(self.dict, {'a': 26, 'b': 2, 'c': 3})
        self.assertEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'a', old=1, new=26),
        ])

        self._mkdict()
        self.dict['d'] = 4
        self.assertEquals(self.dict, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
        self.assertEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'd', new=4)
        ])

    def test_clear(self):
        self.dict.clear()
        self.assertEquals(self.dict, {})
        # We don't know in which order the items are cleared
        self.assertItemsEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'a', old=1),
            ChangeRecord.item(self.dict, 'b', old=2),
            ChangeRecord.item(self.dict, 'c', old=3)
        ])

    def test_pop(self):
        result = self.dict.pop('a')
        self.assertEqual(result, 1)
        self.assertEqual(self.dict, {'b': 2, 'c': 3})
        self.assertEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'a', old=1)
        ])

    def test_popitem(self):
        k, v = self.dict.popitem()
        self.assertFalse(k in self.dict)
        self.assertEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, k, old=v)
        ])

    def test_setdefault(self):
        self.dict.setdefault('a', 4)
        self.assertEqual(self.dict, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(self.observer.changes, [])

        self.dict.setdefault('d', 4)
        self.assertEqual(self.dict, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
        self.assertEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'd', new=4)
        ])

    def test_update(self):
        self.dict.update({'d': 5}, c=6, f=7)
        self.assertEqual(self.dict, {'a': 1, 'b': 2, 'c': 6, 'd': 5, 'f': 7})
        self.assertItemsEqual(self.observer.changes, [
            ChangeRecord.item(self.dict, 'c', old=3, new=6),
            ChangeRecord.item(self.dict, 'd', new=5),
            ChangeRecord.item(self.dict, 'f', new=7)
        ])
