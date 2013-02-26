from __future__ import absolute_import

from operator import attrgetter

from django.test import TestCase

from .models import Person


class RecursiveM2MTests(TestCase):
    def test_recursive_m2m(self):
        a, b, c, d = [
            Person.objects.create(name=name)
            for name in ["Anne", "Bill", "Chuck", "David"]
        ]

        # Add some friends in the direction of field definition
        # Anne is friends with Bill and Chuck
        a.friends.add(b, c)

        # David is friends with Anne and Chuck - add in reverse direction
        d.friends.add(a,c)

        # Who is friends with Anne?
        self.assertQuerysetEqual(
            a.friends.all(), [
                "Bill",
                "Chuck",
                "David"
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            b.friends.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who is friends with Chuck?
        self.assertQuerysetEqual(
            c.friends.all(), [
                "Anne",
                "David"
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with David?
        self.assertQuerysetEqual(
            d.friends.all(), [
                "Anne",
                "Chuck",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Bill is already friends with Anne - add Anne again, but in the
        # reverse direction
        b.friends.add(a)

        # Who is friends with Anne?
        self.assertQuerysetEqual(
            a.friends.all(), [
                "Bill",
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            b.friends.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Remove Anne from Bill's friends
        b.friends.remove(a)
        # Who is friends with Anne?
        self.assertQuerysetEqual(
            a.friends.all(), [
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is friends with Bill?
        self.assertQuerysetEqual(
            b.friends.all(), []
        )

        # Clear Anne's group of friends
        a.friends.clear()
        # Who is friends with Anne?
        self.assertQuerysetEqual(
            a.friends.all(), []
        )
        # Reverse relationships should also be gone
        # Who is friends with Chuck?
        self.assertQuerysetEqual(
            c.friends.all(), [
                "David",
            ],
            attrgetter("name")
        )
        # Who is friends with David?
        self.assertQuerysetEqual(
            d.friends.all(), [
                "Chuck",
            ],
            attrgetter("name")
        )

        # Add some idols in the direction of field definition
        # Anne idolizes Bill and Chuck
        a.idols.add(b, c)
        # Bill idolizes Anne right back
        b.idols.add(a)
        # David is idolized by Anne and Chuck - add in reverse direction
        d.stalkers.add(a, c)

        # Who are Anne's idols?
        self.assertQuerysetEqual(
            a.idols.all(), [
                "Bill",
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is stalking Anne?
        self.assertQuerysetEqual(
            a.stalkers.all(), [
                "Bill",
            ],
            attrgetter("name")
        )
        # Who are Bill's idols?
        self.assertQuerysetEqual(
            b.idols.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who is stalking Bill?
        self.assertQuerysetEqual(
            b.stalkers.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who are Chuck's idols?
        self.assertQuerysetEqual(
            c.idols.all(), [
                "David",
            ],
            attrgetter("name"),
        )
        # Who is stalking Chuck?
        self.assertQuerysetEqual(
            c.stalkers.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who are David's idols?
        self.assertQuerysetEqual(
            d.idols.all(), []
        )
        # Who is stalking David
        self.assertQuerysetEqual(
            d.stalkers.all(), [
                "Anne",
                "Chuck",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Bill is already being stalked by Anne - add Anne again, but in the
        # reverse direction
        b.stalkers.add(a)
        # Who are Anne's idols?
        self.assertQuerysetEqual(
            a.idols.all(), [
                "Bill",
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is stalking Anne?
        self.assertQuerysetEqual(
            a.stalkers.all(), [
                "Bill",
            ],
            attrgetter("name")
        )
        # Who are Bill's idols
        self.assertQuerysetEqual(
            b.idols.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who is stalking Bill?
        self.assertQuerysetEqual(
            b.stalkers.all(), [
                "Anne",
            ],
            attrgetter("name"),
        )
        # Remove Anne from Bill's list of stalkers
        b.stalkers.remove(a)
        # Who are Anne's idols?
        self.assertQuerysetEqual(
            a.idols.all(), [
                "Chuck",
                "David",
            ],
            attrgetter("name"),
            ordered=False
        )
        # Who is stalking Anne?
        self.assertQuerysetEqual(
            a.stalkers.all(), [
                "Bill",
            ],
            attrgetter("name")
        )
        # Who are Bill's idols?
        self.assertQuerysetEqual(
            b.idols.all(), [
                "Anne",
            ],
            attrgetter("name")
        )
        # Who is stalking Bill?
        self.assertQuerysetEqual(
            b.stalkers.all(), []
        )
        # Clear Anne's group of idols
        a.idols.clear()
        # Who are Anne's idols
        self.assertQuerysetEqual(
            a.idols.all(), []
        )
        # Reverse relationships should also be gone
        # Who is stalking Chuck?
        self.assertQuerysetEqual(
            c.stalkers.all(), []
        )
        # Who is friends with David?
        self.assertQuerysetEqual(
            d.stalkers.all(), [
                "Chuck",
            ],
            attrgetter("name")
        )
