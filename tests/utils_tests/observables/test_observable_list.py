from django.test import TestCase
from django.utils.observables import ObservableList, ChangeRecord


class Observer(object):
    def __init__(self):
        self.changes = list()

    def handle_changes(self, change_records):
        self.changes.extend(change_records)


class TestObservableList(TestCase):
    def setUp(self):
        self.observer = Observer()
        self._mklist(range(3))

    def _mklist(self, li):
        self.observer.changes.clear()
        self.list = ObservableList(li)
        self.list.add_observer(self.observer)

    def test_setitem(self):
        self.list[1] = 'hello'
        self.assertEqual(self.list, [0, 'hello', 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 1, old=1, new='hello')
            ]
        )

        # Using a negative.item should create records with a positive.item
        self._mklist(range(3))
        self.list[-2] = 'world'
        self.assertEqual(self.list, [0, 'world', 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 1, old=1, new='world'),
            ]
        )

    def test_setitem_slice(self):
        self._mklist(range(10))

        self.list[3:8] = ['a', 'b']
        self.assertEqual(self.list, [0, 1, 2, 'a', 'b', 8, 9])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 7, old=7),
                ChangeRecord.item(self.list, 6, old=6),
                ChangeRecord.item(self.list, 5, old=5),
                ChangeRecord.item(self.list, 4, old=4),
                ChangeRecord.item(self.list, 3, old=3),
                ChangeRecord.item(self.list, 3, new='b'),
                ChangeRecord.item(self.list, 3, new='a')
            ]
        )

        self._mklist(range(10))
        self.list[0:10:2] = ['a', 'b', 'c', 'd', 'e']
        self.assertEqual(self.list, ['a', 1, 'b', 3, 'c', 5, 'd', 7, 'e', 9])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 0, old=0, new='a'),
                ChangeRecord.item(self.list, 2, old=2, new='b'),
                ChangeRecord.item(self.list, 4, old=4, new='c'),
                ChangeRecord.item(self.list, 6, old=6, new='d'),
                ChangeRecord.item(self.list, 8, old=8, new='e'),
            ]
        )

        self._mklist(range(10))
        self.list[10:0:-2] = ['a', 'b', 'c', 'd', 'e']
        self.assertEqual(self.list, [0, 'e', 2, 'd', 4, 'c', 6, 'b', 8, 'a'])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 9, old=9, new='a'),
                ChangeRecord.item(self.list, 7, old=7, new='b'),
                ChangeRecord.item(self.list, 5, old=5, new='c'),
                ChangeRecord.item(self.list, 3, old=3, new='d'),
                ChangeRecord.item(self.list, 1, old=1, new='e'),
            ]
        )

    def test_delitem(self):
        del self.list[1]
        self.assertEqual(self.list, [0, 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 1, old=1)
            ]
        )

    def test_delitem_slice(self):
        self._mklist(range(10))

        # contiguous items
        del self.list[5:]
        self.assertEqual(self.list, [0, 1, 2, 3, 4])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 9, old=9),
                ChangeRecord.item(self.list, 8, old=8),
                ChangeRecord.item(self.list, 7, old=7),
                ChangeRecord.item(self.list, 6, old=6),
                ChangeRecord.item(self.list, 5, old=5)
            ]
        )

        # non-unit step
        self._mklist(range(10))
        del self.list[0:10:3]
        self.assertEqual(self.list, [1, 2, 4, 5, 7, 8])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 9, old=9),
                ChangeRecord.item(self.list, 6, old=6),
                ChangeRecord.item(self.list, 3, old=3),
                ChangeRecord.item(self.list, 0, old=0)
            ]
        )

        # backwards range. Should still delete items from highest to lowest
        self._mklist(range(10))
        del self.list[10:0:-3]
        self.assertEqual(self.list, [0, 1, 2, 4, 5, 7, 8])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 9, old=9),
                ChangeRecord.item(self.list, 6, old=6),
                ChangeRecord.item(self.list, 3, old=3)
            ]
        )

    def test_inplace_add(self):
        with self.assertRaises(TypeError):
            self.list += ('a', 'b', 'c')

        self.list += ['a', 'b', 'c']
        self.assertEqual(self.list, [0, 1, 2, 'a', 'b', 'c'])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 3, new='a'),
                ChangeRecord.item(self.list, 4, new='b'),
                ChangeRecord.item(self.list, 5, new='c')
            ]
        )

    def test_add(self):
        self.list = self.list + ['a', 'b', 'c']
        self.assertEqual(self.list, [0, 1, 2, 'a', 'b', 'c'])
        self.assertEqual(self.observer.changes, [])

    def test_inplace_mul(self):
        with self.assertRaises(TypeError):
            self.list *= 'a'
        self.list *= 2
        self.assertEqual(self.list, [0, 1, 2, 0, 1, 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 3, new=0),
                ChangeRecord.item(self.list, 4, new=1),
                ChangeRecord.item(self.list, 5, new=2)
            ])
        self.observer.changes.clear()
        self.list *= -1
        self.assertEqual(self.list, [])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 5, old=2),
                ChangeRecord.item(self.list, 4, old=1),
                ChangeRecord.item(self.list, 3, old=0),
                ChangeRecord.item(self.list, 2, old=2),
                ChangeRecord.item(self.list, 1, old=1),
                ChangeRecord.item(self.list, 0, old=0)
            ]
        )

    def test_mul(self):
        self.list = self.list * 2
        self.assertEqual(self.list, [0, 1, 2, 0, 1, 2])
        self.assertEqual(self.observer.changes, [])

    def test_append(self):
        self.list.append('hello')
        self.assertEqual(self.list, [0, 1, 2, 'hello'])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 3, new='hello')
            ]
        )

    def test_insert(self):
        self.list.insert(1, 'hello')
        self.assertEqual(self.list, [0, 'hello', 1, 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 1, new='hello')
            ]
        )

    def test_extend(self):
        self.list.extend(('a', 'b', 'c'))
        self.assertEqual(self.list, [0, 1, 2, 'a', 'b', 'c'])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 3, new='a'),
                ChangeRecord.item(self.list, 4, new='b'),
                ChangeRecord.item(self.list, 5, new='c')
            ]
        )

    def test_clear(self):
        self.list.clear()
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 2, old=2),
                ChangeRecord.item(self.list, 1, old=1),
                ChangeRecord.item(self.list, 0, old=0)
            ]
        )

    def test_pop(self):
        result = self.list.pop(0)
        self.assertEqual(result, 0)
        self.assertEqual(self.list, [1, 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 0, old=0)
            ]
        )

    def test_remove(self):
        with self.assertRaises(ValueError):
            self.list.remove(14)
        self.list.remove(1)
        self.assertEqual(self.list, [0, 2])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 1, old=1)
            ]
        )

    def test_inplace_reverse(self):
        self.list.reverse()
        self.assertEqual(self.list, [2, 1, 0])
        self.assertEqual(
            self.observer.changes,
            [
                ChangeRecord.item(self.list, 0, old=0, new=2),
                ChangeRecord.item(self.list, 2, old=2, new=0),
            ])








