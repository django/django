from datetime import datetime
from operator import attrgetter

from django.db.models import F
from django.db.models.functions import Upper
from django.test import TestCase

from .models import Article, Author, OrderedByFArticle, Reference


class OrderingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.a1 = Article.objects.create(headline="Article 1", pub_date=datetime(2005, 7, 26))
        cls.a2 = Article.objects.create(headline="Article 2", pub_date=datetime(2005, 7, 27))
        cls.a3 = Article.objects.create(headline="Article 3", pub_date=datetime(2005, 7, 27))
        cls.a4 = Article.objects.create(headline="Article 4", pub_date=datetime(2005, 7, 28))
        cls.author_1 = Author.objects.create(name="Name 1")
        cls.author_2 = Author.objects.create(name="Name 2")
        for i in range(2):
            Author.objects.create()

    def test_default_ordering(self):
        """
        By default, Article.objects.all() orders by pub_date descending, then
        headline ascending.
        """
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Article 4",
                "Article 2",
                "Article 3",
                "Article 1",
            ],
            attrgetter("headline")
        )

        # Getting a single item should work too:
        self.assertEqual(Article.objects.all()[0], self.a4)

    def test_default_ordering_override(self):
        """
        Override ordering with order_by, which is in the same format as the
        ordering attribute in models.
        """
        self.assertQuerysetEqual(
            Article.objects.order_by("headline"), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by("pub_date", "-headline"), [
                "Article 1",
                "Article 3",
                "Article 2",
                "Article 4",
            ],
            attrgetter("headline")
        )

    def test_order_by_override(self):
        """
        Only the last order_by has any effect (since they each override any
        previous ordering).
        """
        self.assertQuerysetEqual(
            Article.objects.order_by("id"), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by("id").order_by("-headline"), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_order_by_nulls_first_and_last(self):
        msg = "nulls_first and nulls_last are mutually exclusive"
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.order_by(F("author").desc(nulls_last=True, nulls_first=True))

    def assertQuerysetEqualReversible(self, queryset, sequence):
        self.assertSequenceEqual(queryset, sequence)
        self.assertSequenceEqual(queryset.reverse(), list(reversed(sequence)))

    def test_order_by_nulls_last(self):
        Article.objects.filter(headline="Article 3").update(author=self.author_1)
        Article.objects.filter(headline="Article 4").update(author=self.author_2)
        # asc and desc are chainable with nulls_last.
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(F("author").desc(nulls_last=True), 'headline'),
            [self.a4, self.a3, self.a1, self.a2],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(F("author").asc(nulls_last=True), 'headline'),
            [self.a3, self.a4, self.a1, self.a2],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(Upper("author__name").desc(nulls_last=True), 'headline'),
            [self.a4, self.a3, self.a1, self.a2],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(Upper("author__name").asc(nulls_last=True), 'headline'),
            [self.a3, self.a4, self.a1, self.a2],
        )

    def test_order_by_nulls_first(self):
        Article.objects.filter(headline="Article 3").update(author=self.author_1)
        Article.objects.filter(headline="Article 4").update(author=self.author_2)
        # asc and desc are chainable with nulls_first.
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(F("author").asc(nulls_first=True), 'headline'),
            [self.a1, self.a2, self.a3, self.a4],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(F("author").desc(nulls_first=True), 'headline'),
            [self.a1, self.a2, self.a4, self.a3],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(Upper("author__name").asc(nulls_first=True), 'headline'),
            [self.a1, self.a2, self.a3, self.a4],
        )
        self.assertQuerysetEqualReversible(
            Article.objects.order_by(Upper("author__name").desc(nulls_first=True), 'headline'),
            [self.a1, self.a2, self.a4, self.a3],
        )

    def test_stop_slicing(self):
        """
        Use the 'stop' part of slicing notation to limit the results.
        """
        self.assertQuerysetEqual(
            Article.objects.order_by("headline")[:2], [
                "Article 1",
                "Article 2",
            ],
            attrgetter("headline")
        )

    def test_stop_start_slicing(self):
        """
        Use the 'stop' and 'start' parts of slicing notation to offset the
        result list.
        """
        self.assertQuerysetEqual(
            Article.objects.order_by("headline")[1:3], [
                "Article 2",
                "Article 3",
            ],
            attrgetter("headline")
        )

    def test_random_ordering(self):
        """
        Use '?' to order randomly.
        """
        self.assertEqual(
            len(list(Article.objects.order_by("?"))), 4
        )

    def test_reversed_ordering(self):
        """
        Ordering can be reversed using the reverse() method on a queryset.
        This allows you to extract things like "the last two items" (reverse
        and then take the first two).
        """
        self.assertQuerysetEqual(
            Article.objects.all().reverse()[:2], [
                "Article 1",
                "Article 3",
            ],
            attrgetter("headline")
        )

    def test_reverse_ordering_pure(self):
        qs1 = Article.objects.order_by(F('headline').asc())
        qs2 = qs1.reverse()
        self.assertQuerysetEqual(
            qs1, [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            qs2, [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_no_reordering_after_slicing(self):
        msg = 'Cannot reverse a query once a slice has been taken.'
        qs = Article.objects.all()[0:2]
        with self.assertRaisesMessage(TypeError, msg):
            qs.reverse()
        with self.assertRaisesMessage(TypeError, msg):
            qs.last()

    def test_extra_ordering(self):
        """
        Ordering can be based on fields included from an 'extra' clause
        """
        self.assertQuerysetEqual(
            Article.objects.extra(select={"foo": "pub_date"}, order_by=["foo", "headline"]), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )

    def test_extra_ordering_quoting(self):
        """
        If the extra clause uses an SQL keyword for a name, it will be
        protected by quoting.
        """
        self.assertQuerysetEqual(
            Article.objects.extra(select={"order": "pub_date"}, order_by=["order", "headline"]), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )

    def test_extra_ordering_with_table_name(self):
        self.assertQuerysetEqual(
            Article.objects.extra(order_by=['ordering_article.headline']), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.extra(order_by=['-ordering_article.headline']), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_order_by_pk(self):
        """
        'pk' works as an ordering option in Meta.
        """
        self.assertQuerysetEqual(
            Author.objects.all(),
            list(reversed(range(1, Author.objects.count() + 1))),
            attrgetter("pk"),
        )

    def test_order_by_fk_attname(self):
        """
        ordering by a foreign key by its attribute name prevents the query
        from inheriting its related model ordering option (#19195).
        """
        for i in range(1, 5):
            author = Author.objects.get(pk=i)
            article = getattr(self, "a%d" % (5 - i))
            article.author = author
            article.save(update_fields={'author'})

        self.assertQuerysetEqual(
            Article.objects.order_by('author_id'), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_order_by_f_expression(self):
        self.assertQuerysetEqual(
            Article.objects.order_by(F('headline')), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by(F('headline').asc()), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by(F('headline').desc()), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_order_by_f_expression_duplicates(self):
        """
        A column may only be included once (the first occurrence) so we check
        to ensure there are no duplicates by inspecting the SQL.
        """
        qs = Article.objects.order_by(F('headline').asc(), F('headline').desc())
        sql = str(qs.query).upper()
        fragment = sql[sql.find('ORDER BY'):]
        self.assertEqual(fragment.count('HEADLINE'), 1)
        self.assertQuerysetEqual(
            qs, [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        qs = Article.objects.order_by(F('headline').desc(), F('headline').asc())
        sql = str(qs.query).upper()
        fragment = sql[sql.find('ORDER BY'):]
        self.assertEqual(fragment.count('HEADLINE'), 1)
        self.assertQuerysetEqual(
            qs, [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

    def test_related_ordering_duplicate_table_reference(self):
        """
        An ordering referencing a model with an ordering referencing a model
        multiple time no circular reference should be detected (#24654).
        """
        first_author = Author.objects.create()
        second_author = Author.objects.create()
        self.a1.author = first_author
        self.a1.second_author = second_author
        self.a1.save()
        self.a2.author = second_author
        self.a2.second_author = first_author
        self.a2.save()
        r1 = Reference.objects.create(article_id=self.a1.pk)
        r2 = Reference.objects.create(article_id=self.a2.pk)
        self.assertSequenceEqual(Reference.objects.all(), [r2, r1])

    def test_default_ordering_by_f_expression(self):
        """F expressions can be used in Meta.ordering."""
        articles = OrderedByFArticle.objects.all()
        articles.filter(headline='Article 2').update(author=self.author_2)
        articles.filter(headline='Article 3').update(author=self.author_1)
        self.assertQuerysetEqual(
            articles, ['Article 1', 'Article 4', 'Article 3', 'Article 2'],
            attrgetter('headline')
        )
