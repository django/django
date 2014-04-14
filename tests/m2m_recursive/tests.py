from __future__ import unicode_literals

from operator import attrgetter

from django.test import TestCase

from .models import Person


class RecursiveM2MTests(TestCase):
    def setUp(self):
        self.a, self.b, self.c, self.d = [
            Person.objects.create(name=name)
            for name in ["Anne", "Bill", "Chuck", "David"]
        ]

        # Anne is friends with Bill and Chuck
        self.a.friends.add(self.b, self.c)

        # David is friends with Anne and Chuck - add in reverse direction
        self.d.friends.add(self.a, self.c)

    def test_recursive_m2m_all(self):
        """ Test that m2m relations are reported correctly """
        # Who is friends with Anne?
        self.assertQuerysetEqual(
            self.a.friends.all(), [
                "Bill",
                "Chuck",
                "David"
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            self.b.friends.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who is friends with Chuck?
        self.assertQuerysetEqual(
            self.c.friends.all(), [
                "Anne",
                "David"
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with David?
        self.assertQuerysetEqual(
            self.d.friends.all(), [
                "Anne",
                "Chuck",
            ],
            attrgetter("name"),
            ordered=False
        )

    def test_recursive_m2m_reverse_add(self):
        """ Test reverse m2m relation is consistent """

        # Bill is already friends with Anne - add Anne again, but in the
        # reverse direction
        self.b.friends.add(self.a)

        # Who is friends with Anne?
        self.assertQuerysetEqual(
            self.a.friends.all(), [
                "Bill",
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            self.b.friends.all(), [
                "Anne",
            ],
            attrgetter("name")
        )

    def test_recursive_m2m_remove(self):
        """ Test that we can remove items from an m2m relationship """

        # Remove Anne from Bill's friends
        self.b.friends.remove(self.a)

        # Who is friends with Anne?
        self.assertQuerysetEqual(
            self.a.friends.all(), [
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            self.b.friends.all(), []
        )

    def test_recursive_m2m_clear(self):
        """ Tests the clear method works as expected on m2m fields """

        # Clear Anne's group of friends
        self.a.friends.clear()

        # Who is friends with Anne?
        self.assertQuerysetEqual(
            self.a.friends.all(), []
        )

        # Reverse relationships should also be gone
        # Who is friends with Chuck?
        self.assertQuerysetEqual(
            self.c.friends.all(), [
                "David",
            ],
            attrgetter("name")
        )

        # Who is friends with David?
        self.assertQuerysetEqual(
            self.d.friends.all(), [
                "Chuck",
            ],
            attrgetter("name")
        )

    def test_recursive_m2m_add_via_related_name(self):
        """ Tests that we can add m2m relations via the related_name attribute """

        # David is idolized by Anne and Chuck - add in reverse direction
        self.d.stalkers.add(self.a)

        # Who are Anne's idols?
        self.assertQuerysetEqual(
            self.a.idols.all(), [
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is stalking Anne?
        self.assertQuerysetEqual(
            self.a.stalkers.all(), [],
            attrgetter("name")
        )

    def test_recursive_m2m_add_in_both_directions(self):
        """ Check that adding the same relation twice results in a single relation """

        # Ann idolizes David
        self.a.idols.add(self.d)

        # David is idolized by Anne
        self.d.stalkers.add(self.a)

        # Who are Anne's idols?
        self.assertQuerysetEqual(
            self.a.idols.all(), [
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # As the assertQuerysetEqual uses a set for comparison,
        # check we've only got David listed once
        self.assertEqual(self.a.idols.all().count(), 1)

    def test_recursive_m2m_related_to_self(self):
        """ Check the expected behavior when an instance is related to itself """

        # Ann idolizes herself
        self.a.idols.add(self.a)

        # Who are Anne's idols?
        self.assertQuerysetEqual(
            self.a.idols.all(), [
                "Anne",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is stalking Anne?
        self.assertQuerysetEqual(
            self.a.stalkers.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
