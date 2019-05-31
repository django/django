from django.test import TestCase

from .models import Person


class RecursiveM2MTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b, cls.c, cls.d = [
            Person.objects.create(name=name)
            for name in ['Anne', 'Bill', 'Chuck', 'David']
        ]
        cls.a.friends.add(cls.b, cls.c)
        # Add m2m for Anne and Chuck in reverse direction.
        cls.d.friends.add(cls.a, cls.c)

    def test_recursive_m2m_all(self):
        for person, friends in (
            (self.a, [self.b, self.c, self.d]),
            (self.b, [self.a]),
            (self.c, [self.a, self.d]),
            (self.d, [self.a, self.c]),
        ):
            with self.subTest(person=person):
                self.assertSequenceEqual(person.friends.all(), friends)

    def test_recursive_m2m_reverse_add(self):
        # Add m2m for Anne in reverse direction.
        self.b.friends.add(self.a)
        self.assertSequenceEqual(self.a.friends.all(), [self.b, self.c, self.d])
        self.assertSequenceEqual(self.b.friends.all(), [self.a])

    def test_recursive_m2m_remove(self):
        self.b.friends.remove(self.a)
        self.assertSequenceEqual(self.a.friends.all(), [self.c, self.d])
        self.assertSequenceEqual(self.b.friends.all(), [])

    def test_recursive_m2m_clear(self):
        # Clear m2m for Anne.
        self.a.friends.clear()
        self.assertSequenceEqual(self.a.friends.all(), [])
        # Reverse m2m relationships should be removed.
        self.assertSequenceEqual(self.c.friends.all(), [self.d])
        self.assertSequenceEqual(self.d.friends.all(), [self.c])

    def test_recursive_m2m_add_via_related_name(self):
        # Add m2m with custom related name for Anne in reverse direction.
        self.d.stalkers.add(self.a)
        self.assertSequenceEqual(self.a.idols.all(), [self.d])
        self.assertSequenceEqual(self.a.stalkers.all(), [])

    def test_recursive_m2m_add_in_both_directions(self):
        # Adding the same relation twice results in a single relation.
        self.a.idols.add(self.d)
        self.d.stalkers.add(self.a)
        self.assertSequenceEqual(self.a.idols.all(), [self.d])

    def test_recursive_m2m_related_to_self(self):
        self.a.idols.add(self.a)
        self.assertSequenceEqual(self.a.idols.all(), [self.a])
        self.assertSequenceEqual(self.a.stalkers.all(), [self.a])
