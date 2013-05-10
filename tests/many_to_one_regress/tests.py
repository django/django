from __future__ import absolute_import

from django.db import models
from django.test import TestCase
from django.utils import six

from .models import (
    First, Third, Parent, Child, Category, Record, Relation, Car, Driver)


class ManyToOneRegressionTests(TestCase):
    def test_object_creation(self):
        Third.objects.create(id='3', name='An example')
        parent = Parent(name='fred')
        parent.save()
        Child.objects.create(name='bam-bam', parent=parent)

    def test_fk_assignment_and_related_object_cache(self):
        # Tests of ForeignKey assignment and the related-object cache (see #6886).

        p = Parent.objects.create(name="Parent")
        c = Child.objects.create(name="Child", parent=p)

        # Look up the object again so that we get a "fresh" object.
        c = Child.objects.get(name="Child")
        p = c.parent

        # Accessing the related object again returns the exactly same object.
        self.assertTrue(c.parent is p)

        # But if we kill the cache, we get a new object.
        del c._parent_cache
        self.assertFalse(c.parent is p)

        # Assigning a new object results in that object getting cached immediately.
        p2 = Parent.objects.create(name="Parent 2")
        c.parent = p2
        self.assertTrue(c.parent is p2)

        # Assigning None succeeds if field is null=True.
        p.bestchild = None
        self.assertTrue(p.bestchild is None)

        # bestchild should still be None after saving.
        p.save()
        self.assertTrue(p.bestchild is None)

        # bestchild should still be None after fetching the object again.
        p = Parent.objects.get(name="Parent")
        self.assertTrue(p.bestchild is None)

        # Assigning None fails: Child.parent is null=False.
        self.assertRaises(ValueError, setattr, c, "parent", None)

        # You also can't assign an object of the wrong type here
        self.assertRaises(ValueError, setattr, c, "parent", First(id=1, second=1))

        # Nor can you explicitly assign None to Child.parent during object
        # creation (regression for #9649).
        self.assertRaises(ValueError, Child, name='xyzzy', parent=None)
        self.assertRaises(ValueError, Child.objects.create, name='xyzzy', parent=None)

        # Creation using keyword argument should cache the related object.
        p = Parent.objects.get(name="Parent")
        c = Child(parent=p)
        self.assertTrue(c.parent is p)

        # Creation using keyword argument and unsaved related instance (#8070).
        p = Parent()
        c = Child(parent=p)
        self.assertTrue(c.parent is p)

        # Creation using attname keyword argument and an id will cause the
        # related object to be fetched.
        p = Parent.objects.get(name="Parent")
        c = Child(parent_id=p.id)
        self.assertFalse(c.parent is p)
        self.assertEqual(c.parent, p)

    def test_multiple_foreignkeys(self):
        # Test of multiple ForeignKeys to the same model (bug #7125).
        c1 = Category.objects.create(name='First')
        c2 = Category.objects.create(name='Second')
        c3 = Category.objects.create(name='Third')
        r1 = Record.objects.create(category=c1)
        r2 = Record.objects.create(category=c1)
        r3 = Record.objects.create(category=c2)
        r4 = Record.objects.create(category=c2)
        r5 = Record.objects.create(category=c3)
        r = Relation.objects.create(left=r1, right=r2)
        r = Relation.objects.create(left=r3, right=r4)
        r = Relation.objects.create(left=r1, right=r3)
        r = Relation.objects.create(left=r5, right=r2)
        r = Relation.objects.create(left=r3, right=r2)

        q1 = Relation.objects.filter(left__category__name__in=['First'], right__category__name__in=['Second'])
        self.assertQuerysetEqual(q1, ["<Relation: First - Second>"])

        q2 = Category.objects.filter(record__left_set__right__category__name='Second').order_by('name')
        self.assertQuerysetEqual(q2, ["<Category: First>", "<Category: Second>"])

        p = Parent.objects.create(name="Parent")
        c = Child.objects.create(name="Child", parent=p)
        self.assertRaises(ValueError, Child.objects.create, name="Grandchild", parent=c)

    def test_fk_instantiation_outside_model(self):
        # Regression for #12190 -- Should be able to instantiate a FK outside
        # of a model, and interrogate its related field.
        cat = models.ForeignKey(Category)
        self.assertEqual('id', cat.rel.get_related_field().name)

    def test_relation_unsaved(self):
        # Test that the <field>_set manager does not join on Null value fields (#17541)
        Third.objects.create(name='Third 1')
        Third.objects.create(name='Third 2')
        th = Third(name="testing")
        # The object isn't saved an thus the relation field is null - we won't even
        # execute a query in this case.
        with self.assertNumQueries(0):
            self.assertEqual(th.child_set.count(), 0)
        th.save()
        # Now the model is saved, so we will need to execute an query.
        with self.assertNumQueries(1):
            self.assertEqual(th.child_set.count(), 0)

    def test_related_null_to_field(self):
        c1 = Car.objects.create()
        c2 = Car.objects.create()
        d1 = Driver.objects.create()
        self.assertIs(d1.car, None)
        with self.assertNumQueries(0):
            self.assertEqual(list(c1.drivers.all()), [])
