from django.test import TestCase

from django.contrib.admin.util import NestedObjects

from models import Count


class NestedObjectsTests(TestCase):
    """
    Tests for ``NestedObject`` utility collection.

    """
    def setUp(self):
        self.n = NestedObjects()
        self.objs = [Count.objects.create(num=i) for i in range(5)]

    def _check(self, target):
        self.assertEquals(self.n.nested(lambda obj: obj.num), target)

    def _add(self, obj, parent=None):
        # don't bother providing the extra args that NestedObjects ignores
        self.n.add(None, None, obj, None, parent)

    def test_unrelated_roots(self):
        self._add(self.objs[0])
        self._add(self.objs[1])
        self._add(self.objs[2], self.objs[1])

        self._check([0, 1, [2]])

    def test_siblings(self):
        self._add(self.objs[0])
        self._add(self.objs[1], self.objs[0])
        self._add(self.objs[2], self.objs[0])

        self._check([0, [1, 2]])

    def test_duplicate_instances(self):
        self._add(self.objs[0])
        self._add(self.objs[1])
        dupe = Count.objects.get(num=1)
        self._add(dupe, self.objs[0])

        self._check([0, 1])

    def test_non_added_parent(self):
        self._add(self.objs[0], self.objs[1])

        self._check([0])

    def test_cyclic(self):
        self._add(self.objs[0], self.objs[2])
        self._add(self.objs[1], self.objs[0])
        self._add(self.objs[2], self.objs[1])
        self._add(self.objs[0], self.objs[2])

        self._check([0, [1, [2]]])

