from django.test import TestCase

from .models import Category, Person


class ManyToOneRecursiveTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.r = Category(id=None, name='Root category', parent=None)
        cls.r.save()
        cls.c = Category(id=None, name='Child category', parent=cls.r)
        cls.c.save()

    def test_m2o_recursive(self):
        self.assertQuerysetEqual(self.r.child_set.all(),
                                 ['<Category: Child category>'])
        self.assertEqual(self.r.child_set.get(name__startswith='Child').id, self.c.id)
        self.assertIsNone(self.r.parent)
        self.assertQuerysetEqual(self.c.child_set.all(), [])
        self.assertEqual(self.c.parent.id, self.r.id)


class MultipleManyToOneRecursiveTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.dad = Person(full_name='John Smith Senior', mother=None, father=None)
        cls.dad.save()
        cls.mom = Person(full_name='Jane Smith', mother=None, father=None)
        cls.mom.save()
        cls.kid = Person(full_name='John Smith Junior', mother=cls.mom, father=cls.dad)
        cls.kid.save()

    def test_m2o_recursive2(self):
        self.assertEqual(self.kid.mother.id, self.mom.id)
        self.assertEqual(self.kid.father.id, self.dad.id)
        self.assertQuerysetEqual(self.dad.fathers_child_set.all(),
                                 ['<Person: John Smith Junior>'])
        self.assertQuerysetEqual(self.mom.mothers_child_set.all(),
                                 ['<Person: John Smith Junior>'])
        self.assertQuerysetEqual(self.kid.mothers_child_set.all(), [])
        self.assertQuerysetEqual(self.kid.fathers_child_set.all(), [])
