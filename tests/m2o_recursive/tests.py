from __future__ import unicode_literals

from django.test import TestCase

from .models import Category, Person


class ManyToOneRecursiveTests(TestCase):

    def setUp(self):
        self.r = Category(id=None, name='Root category', parent=None)
        self.r.save()
        self.c = Category(id=None, name='Child category', parent=self.r)
        self.c.save()

    def test_m2o_recursive(self):
        self.assertQuerysetEqual(self.r.child_set.all(),
                                 ['<Category: Child category>'])
        self.assertEqual(self.r.child_set.get(name__startswith='Child').id, self.c.id)
        self.assertEqual(self.r.parent, None)
        self.assertQuerysetEqual(self.c.child_set.all(), [])
        self.assertEqual(self.c.parent.id, self.r.id)


class MultipleManyToOneRecursiveTests(TestCase):

    def setUp(self):
        self.dad = Person(full_name='John Smith Senior', mother=None, father=None)
        self.dad.save()
        self.mom = Person(full_name='Jane Smith', mother=None, father=None)
        self.mom.save()
        self.kid = Person(full_name='John Smith Junior', mother=self.mom, father=self.dad)
        self.kid.save()

    def test_m2o_recursive2(self):
        self.assertEqual(self.kid.mother.id, self.mom.id)
        self.assertEqual(self.kid.father.id, self.dad.id)
        self.assertQuerysetEqual(self.dad.fathers_child_set.all(),
                                 ['<Person: John Smith Junior>'])
        self.assertQuerysetEqual(self.mom.mothers_child_set.all(),
                                 ['<Person: John Smith Junior>'])
        self.assertQuerysetEqual(self.kid.mothers_child_set.all(), [])
        self.assertQuerysetEqual(self.kid.fathers_child_set.all(), [])
