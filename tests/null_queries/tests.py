from django.core.exceptions import FieldError
from django.test import TestCase

from .models import Choice, Inner, OuterA, OuterB, Poll


class NullQueriesTests(TestCase):

    def test_none_as_null(self):
        """
        Regression test for the use of None as a query value.

        None is interpreted as an SQL NULL, but only in __exact and __iexact
        queries.
        Set up some initial polls and choices
        """
        p1 = Poll(question='Why?')
        p1.save()
        c1 = Choice(poll=p1, choice='Because.')
        c1.save()
        c2 = Choice(poll=p1, choice='Why Not?')
        c2.save()

        # Exact query with value None returns nothing ("is NULL" in sql,
        # but every 'id' field has a value).
        self.assertQuerysetEqual(Choice.objects.filter(choice__exact=None), [])

        # The same behavior for iexact query.
        self.assertQuerysetEqual(Choice.objects.filter(choice__iexact=None), [])

        # Excluding the previous result returns everything.
        self.assertQuerysetEqual(
            Choice.objects.exclude(choice=None).order_by('id'),
            [
                '<Choice: Choice: Because. in poll Q: Why? >',
                '<Choice: Choice: Why Not? in poll Q: Why? >'
            ]
        )

        # Valid query, but fails because foo isn't a keyword
        with self.assertRaises(FieldError):
            Choice.objects.filter(foo__exact=None)

        # Can't use None on anything other than __exact and __iexact
        with self.assertRaises(ValueError):
            Choice.objects.filter(id__gt=None)

        # Related managers use __exact=None implicitly if the object hasn't been saved.
        p2 = Poll(question="How?")
        self.assertEqual(repr(p2.choice_set.all()), '<QuerySet []>')

    def test_reverse_relations(self):
        """
        Querying across reverse relations and then another relation should
        insert outer joins correctly so as not to exclude results.
        """
        obj = OuterA.objects.create()
        self.assertQuerysetEqual(
            OuterA.objects.filter(inner__third=None),
            ['<OuterA: OuterA object>']
        )
        self.assertQuerysetEqual(
            OuterA.objects.filter(inner__third__data=None),
            ['<OuterA: OuterA object>']
        )

        Inner.objects.create(first=obj)
        self.assertQuerysetEqual(
            Inner.objects.filter(first__inner__third=None),
            ['<Inner: Inner object>']
        )

        # Ticket #13815: check if <reverse>_isnull=False does not produce
        # faulty empty lists
        OuterB.objects.create(data="reverse")
        self.assertQuerysetEqual(
            OuterB.objects.filter(inner__isnull=False),
            []
        )
        Inner.objects.create(first=obj)
        self.assertQuerysetEqual(
            OuterB.objects.exclude(inner__isnull=False),
            ['<OuterB: OuterB object>']
        )
