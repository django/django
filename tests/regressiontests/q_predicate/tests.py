import datetime

from django.contrib.sessions.models import Session, SessionManager
from django.db.models.query import Q
from django.utils import six, unittest
from django import test

from .models import Item, OtherItem

class QasPredicateTest(test.TestCase):
    def setUp(self):
        self.testobj = Item.objects.create(
                name="hello world",
                int_value=50,
                created=datetime.datetime.now(),
                )

        self.testobj2 = Item.objects.create(
                name="bye world",
                int_value=10,
                created=datetime.datetime.now(),
                parent=self.testobj
                )

    def test_exact(self):
        self.assertTrue(Q(name__exact='hello world').matches(self.testobj))
        self.assertTrue(Q(name='hello world').matches(self.testobj))
        self.assertFalse(Q(name='Hello world').matches(self.testobj))
        self.assertFalse(Q(name='hello worl').matches(self.testobj))
        self.assertTrue(Q(parent__name__exact='hello world').matches(self.testobj2))

    def test_iexact(self):
        self.assertTrue(Q(name__iexact='heLLo World').matches(self.testobj))
        self.assertFalse(Q(name__iexact='hello worl').matches(self.testobj))

    def test_contains(self):
        self.assertTrue(Q(name__contains='hello').matches(self.testobj))
        self.assertFalse(Q(name__contains='foobar').matches(self.testobj))

    def test_icontains(self):
        self.assertTrue(Q(name__icontains='heLLo').matches(self.testobj))

    def test_gt(self):
        self.assertTrue(Q(int_value__gt=20).matches(self.testobj))
        self.assertFalse(Q(int_value__gt=80).matches(self.testobj))
        self.assertTrue(Q(int_value__gt=20.0).matches(self.testobj))
        self.assertFalse(Q(int_value__gt=80.0).matches(self.testobj))
        self.assertFalse(Q(int_value__gt=50).matches(self.testobj))

    def test_gte(self):
        self.assertTrue(Q(int_value__gte=20).matches(self.testobj))
        self.assertTrue(Q(int_value__gte=50).matches(self.testobj))

    def test_lt(self):
        self.assertFalse(Q(int_value__lt=20).matches(self.testobj))
        self.assertTrue(Q(int_value__lt=80).matches(self.testobj))
        self.assertFalse(Q(int_value__lt=20.0).matches(self.testobj))
        self.assertTrue(Q(int_value__lt=80.0).matches(self.testobj))
        self.assertFalse(Q(int_value__lt=50).matches(self.testobj))

    def test_lte(self):
        self.assertFalse(Q(int_value__lte=20).matches(self.testobj))
        self.assertTrue(Q(int_value__lte=50).matches(self.testobj))

    def test_startswith(self):
        self.assertTrue(Q(name__startswith='hello').matches(self.testobj))
        self.assertFalse(Q(name__startswith='world').matches(self.testobj))
        self.assertFalse(Q(name__startswith='Hello').matches(self.testobj))

    def test_istartswith(self):
        self.assertTrue(Q(name__istartswith='heLLo').matches(self.testobj))
        self.assertFalse(Q(name__startswith='world').matches(self.testobj))

    def test_endswith(self):
        self.assertFalse(Q(name__endswith='hello').matches(self.testobj))
        self.assertTrue(Q(name__endswith='world').matches(self.testobj))
        self.assertFalse(Q(name__endswith='World').matches(self.testobj))

    def test_iendswith(self):
        self.assertFalse(Q(name__iendswith='hello').matches(self.testobj))
        self.assertTrue(Q(name__iendswith='World').matches(self.testobj))

    def test_dates(self):
        today = datetime.date.today()
        self.assertTrue(Q(created__year=today.year).matches(self.testobj))
        self.assertTrue(Q(created__month=today.month).matches(self.testobj))
        self.assertTrue(Q(created__day=today.day).matches(self.testobj))
        self.assertTrue(Q(created__week_day=today.weekday()).matches(self.testobj))

        self.assertFalse(Q(created__year=today.year + 1).matches(self.testobj))
        self.assertFalse(Q(created__month=today.month + 1).matches(self.testobj))
        self.assertFalse(Q(created__day=today.day + 1).matches(self.testobj))
        self.assertFalse(Q(created__week_day=today.weekday() + 1).matches(self.testobj))

    def test_null(self):
        self.assertTrue(Q(parent__isnull=True).matches(self.testobj))
        self.assertFalse(Q(parent__isnull=False).matches(self.testobj))

    def test_regex(self):
        self.assertTrue(Q(name__regex='hel*o').matches(self.testobj))
        self.assertFalse(Q(name__regex='Hel*o').matches(self.testobj))

    def test_iregex(self):
        self.assertTrue(Q(name__iregex='Hel*o').matches(self.testobj))

    def test_simple_negation(self):
        predicate = ~Q(name__contains='world')
        self.assertFalse(predicate.matches(self.testobj))

    def test_negation2(self):
        p1 = ~Q(name__contains='y')
        p2 = ~Q(name__contains='b')
        p2_2 = ~Q(name__contains='h')
        p3 = p1 & p2
        self.assertTrue(p3.matches(self.testobj))
        # Note you can't invert Q at the same time you call .matches
        p3_2 = ~p3
        self.assertFalse(p3_2.matches(self.testobj))
        self.assertFalse(p3.matches(self.testobj2))
        p4 = Q(name__contains='e')
        p5 = p1 | p4
        self.assertTrue(p5.matches(self.testobj))
        self.assertTrue(p5.matches(self.testobj2))
        p6 = p1 & p5
        self.assertTrue(p6.matches(self.testobj))
        self.assertFalse(p6.matches(self.testobj2))

    def test_invalid_lookup(self):
        """
        Test that an invalid lookup raises an exception
        """
        predicate = Q(name__hazawat=5)
        with six.assertRaisesRegex(self, ValueError, 'invalid lookup'):
            predicate.matches(self.testobj)

    def test_invalid_field_name(self):
        predicate = Q(flubber__contains='foo')
        with six.assertRaisesRegex(self, ValueError, 'invalid lookup'):
            predicate.matches(self.testobj)

class RelationshipFollowTest(test.TestCase):

    def setUp(self):
        self.testobj = Item.objects.create(
                name="hello world",
                int_value=50,
                created=datetime.datetime.now(),
                )

        self.testobj2 = Item.objects.create(
                name="bye world",
                int_value=10,
                created=datetime.datetime.now(),
                parent=self.testobj
                )

        self.testobj3 = Item.objects.create(
                name="strange world",
                int_value=1000,
                created=datetime.datetime.now(),
                parent=self.testobj2
                )

    def test_simple_follow(self):
        self.assertTrue(Q(parent__parent__name='hello world').matches(self.testobj3))

    def test_nonexist_follow(self):
        self.assertFalse(Q(parent__parent__name='hello world').matches(self.testobj))

    def test_follow_isnull(self):
        """
        Following a non-existant relationship, but testing for isnull
        should return True
        """
        self.assertTrue(Q(parent__int_value__isnull=True).matches(self.testobj))

class ManagerTests(test.TestCase):

    def setUp(self):
        self.testobj = Item.objects.create(
                name="hello world",
                int_value=50,
                created=datetime.datetime.now(),
                )

        self.testobj2 = OtherItem.objects.create(
                name="bye world",
                int_value=10,
                created=datetime.datetime.now(),
                )

    def test_wrong_manager(self):
        predicate = Q(name__contains='world')

        pmatch = predicate.match_compile(manager=Item.alt_manager)
        pmatch.matches(self.testobj)
        with six.assertRaisesRegex(self, ValueError, 'invalid manager'):
            pmatch.matches(self.testobj2)
        # test that predicat recompiles when used with predicate
        predicate.matches(self.testobj2)
        # test that the newly compiled matcher uses the instance manager
        self.assertEquals(predicate._compiled_matcher.manager,
                self.testobj2._default_manager)
