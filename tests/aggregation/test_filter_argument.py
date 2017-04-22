import datetime
from decimal import Decimal

from django.db.models import Case, Count, F, Q, Sum, When
from django.test import TestCase

from .models import Author, Book, Publisher


class FilteredAggregateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(name='test', age=40)
        cls.a2 = Author.objects.create(name='test2', age=60)
        cls.a3 = Author.objects.create(name='test3', age=100)
        cls.p1 = Publisher.objects.create(name='Apress', num_awards=3, duration=datetime.timedelta(days=1))
        cls.b1 = Book.objects.create(
            isbn='159059725', name='The Definitive Guide to Django: Web Development Done Right',
            pages=447, rating=4.5, price=Decimal('30.00'), contact=cls.a1, publisher=cls.p1,
            pubdate=datetime.date(2007, 12, 6),
        )
        cls.b2 = Book.objects.create(
            isbn='067232959', name='Sams Teach Yourself Django in 24 Hours',
            pages=528, rating=3.0, price=Decimal('23.09'), contact=cls.a2, publisher=cls.p1,
            pubdate=datetime.date(2008, 3, 3),
        )
        cls.b3 = Book.objects.create(
            isbn='159059996', name='Practical Django Projects',
            pages=600, rating=4.5, price=Decimal('29.69'), contact=cls.a3, publisher=cls.p1,
            pubdate=datetime.date(2008, 6, 23),
        )
        cls.a1.friends.add(cls.a2)
        cls.a1.friends.add(cls.a3)
        cls.b1.authors.add(cls.a1)
        cls.b1.authors.add(cls.a3)
        cls.b2.authors.add(cls.a2)
        cls.b3.authors.add(cls.a3)

    def test_filtered_aggregates(self):
        agg = Sum('age', filter=Q(name__startswith='test'))
        self.assertEqual(Author.objects.aggregate(age=agg)['age'], 200)

    def test_double_filtered_aggregates(self):
        agg = Sum('age', filter=Q(Q(name='test2') & ~Q(name='test')))
        self.assertEqual(Author.objects.aggregate(age=agg)['age'], 60)

    def test_excluded_aggregates(self):
        agg = Sum('age', filter=~Q(name='test2'))
        self.assertEqual(Author.objects.aggregate(age=agg)['age'], 140)

    def test_related_aggregates_m2m(self):
        agg = Sum('friends__age', filter=~Q(friends__name='test'))
        self.assertEqual(Author.objects.filter(name='test').aggregate(age=agg)['age'], 160)

    def test_related_aggregates_m2m_and_fk(self):
        q = Q(friends__book__publisher__name='Apress') & ~Q(friends__name='test3')
        agg = Sum('friends__book__pages', filter=q)
        self.assertEqual(Author.objects.filter(name='test').aggregate(pages=agg)['pages'], 528)

    def test_plain_annotate(self):
        agg = Sum('book__pages', filter=Q(book__rating__gt=3))
        qs = Author.objects.annotate(pages=agg).order_by('pk')
        self.assertSequenceEqual([a.pages for a in qs], [447, None, 1047])

    def test_filtered_aggregate_on_annotate(self):
        pages_annotate = Sum('book__pages', filter=Q(book__rating__gt=3))
        age_agg = Sum('age', filter=Q(total_pages__gte=400))
        aggregated = Author.objects.annotate(total_pages=pages_annotate).aggregate(summed_age=age_agg)
        self.assertEqual(aggregated, {'summed_age': 140})

    def test_case_aggregate(self):
        agg = Sum(
            Case(When(friends__age=40, then=F('friends__age'))),
            filter=Q(friends__name__startswith='test'),
        )
        self.assertEqual(Author.objects.aggregate(age=agg)['age'], 80)

    def test_sum_star_exception(self):
        msg = 'Star cannot be used with filter. Please specify a field.'
        with self.assertRaisesMessage(ValueError, msg):
            Count('*', filter=Q(age=40))
