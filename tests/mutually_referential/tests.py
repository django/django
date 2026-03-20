from django.test import TestCase

from .models import Child, Parent


class MutuallyReferentialTests(TestCase):
    def test_mutually_referential(self):
        # Create a Parent
        q = Parent(name="Elizabeth")
        q.save()

        # Create some children
        c = q.child_set.create(name="Charles")
        q.child_set.create(name="Edward")

        # Set the best child
        # No assertion require here; if basic assignment and
        # deletion works, the test passes.
        q.bestchild = c
        q.save()
        q.delete()

    def test_forward_reference(self):
        p = Parent.objects.create(name="Diana")
        c = Child.objects.create(name="William", parent=p)
        p.bestchild = c
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.bestchild, c)

    def test_reverse_reference(self):
        p = Parent.objects.create(name="George")
        c1 = Child.objects.create(name="Harry", parent=p)
        c2 = Child.objects.create(name="Archie", parent=p)
        self.assertQuerySetEqual(
            p.child_set.order_by("name"),
            ["Archie", "Harry"],
            lambda c: c.name,
        )
        self.assertEqual(c1.parent, p)
        self.assertEqual(c2.parent, p)

    def test_bestchild_null(self):
        p = Parent.objects.create(name="Anne")
        self.assertIsNone(p.bestchild)

    def test_favored_by_reverse(self):
        p = Parent.objects.create(name="Philip")
        c = Child.objects.create(name="Andrew", parent=p)
        p.bestchild = c
        p.save()
        self.assertIn(p, c.favored_by.all())
