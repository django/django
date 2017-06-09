import datetime
from operator import attrgetter

from django.core.exceptions import ValidationError
from django.db import router
from django.db.models.sql import InsertQuery
from django.test import TestCase, skipUnlessDBFeature
from django.utils.timezone import get_fixed_timezone

from .models import (
    Article, Department, Event, Model1, Model2, Model3, NonAutoPK, Party,
    Worker,
)


class ModelTests(TestCase):
    def test_model_init_too_many_args(self):
        msg = "Number of args exceeds number of fields"
        with self.assertRaisesMessage(IndexError, msg):
            Worker(1, 2, 3, 4)

    # The bug is that the following queries would raise:
    # "TypeError: Related Field has invalid lookup: gte"
    def test_related_gte_lookup(self):
        """
        Regression test for #10153: foreign key __gte lookups.
        """
        Worker.objects.filter(department__gte=0)

    def test_related_lte_lookup(self):
        """
        Regression test for #10153: foreign key __lte lookups.
        """
        Worker.objects.filter(department__lte=0)

    def test_sql_insert_compiler_return_id_attribute(self):
        """
        Regression test for #14019: SQLInsertCompiler.as_sql() failure
        """
        db = router.db_for_write(Party)
        query = InsertQuery(Party)
        query.insert_values([Party._meta.fields[0]], [], raw=False)
        # this line will raise an AttributeError without the accompanying fix
        query.get_compiler(using=db).as_sql()

    def test_empty_choice(self):
        # NOTE: Part of the regression test here is merely parsing the model
        # declaration. The verbose_name, in particular, did not always work.
        a = Article.objects.create(
            headline="Look at me!", pub_date=datetime.datetime.now()
        )
        # An empty choice field should return None for the display name.
        self.assertIs(a.get_status_display(), None)

        # Empty strings should be returned as string
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(a.misc_data, '')

    def test_long_textfield(self):
        # TextFields can hold more than 4000 characters (this was broken in
        # Oracle).
        a = Article.objects.create(
            headline="Really, really big",
            pub_date=datetime.datetime.now(),
            article_text="ABCDE" * 1000
        )
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(len(a.article_text), 5000)

    def test_long_unicode_textfield(self):
        # TextFields can hold more than 4000 bytes also when they are
        # less than 4000 characters
        a = Article.objects.create(
            headline="Really, really big",
            pub_date=datetime.datetime.now(),
            article_text='\u05d0\u05d1\u05d2' * 1000
        )
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(len(a.article_text), 3000)

    def test_date_lookup(self):
        # Regression test for #659
        Party.objects.create(when=datetime.datetime(1999, 12, 31))
        Party.objects.create(when=datetime.datetime(1998, 12, 31))
        Party.objects.create(when=datetime.datetime(1999, 1, 1))
        Party.objects.create(when=datetime.datetime(1, 3, 3))
        self.assertQuerysetEqual(
            Party.objects.filter(when__month=2), []
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__month=1), [
                datetime.date(1999, 1, 1)
            ],
            attrgetter("when")
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__month=12), [
                datetime.date(1999, 12, 31),
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when"),
            ordered=False
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__year=1998), [
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when")
        )
        # Regression test for #8510
        self.assertQuerysetEqual(
            Party.objects.filter(when__day="31"), [
                datetime.date(1999, 12, 31),
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when"),
            ordered=False
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__month="12"), [
                datetime.date(1999, 12, 31),
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when"),
            ordered=False
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__year="1998"), [
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when")
        )

        # Regression test for #18969
        self.assertQuerysetEqual(
            Party.objects.filter(when__year=1), [
                datetime.date(1, 3, 3),
            ],
            attrgetter("when")
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__year='1'), [
                datetime.date(1, 3, 3),
            ],
            attrgetter("when")
        )

    def test_date_filter_null(self):
        # Date filtering was failing with NULL date values in SQLite
        # (regression test for #3501, among other things).
        Party.objects.create(when=datetime.datetime(1999, 1, 1))
        Party.objects.create()
        p = Party.objects.filter(when__month=1)[0]
        self.assertEqual(p.when, datetime.date(1999, 1, 1))
        self.assertQuerysetEqual(
            Party.objects.filter(pk=p.pk).dates("when", "month"), [
                1
            ],
            attrgetter("month")
        )

    def test_get_next_prev_by_field(self):
        # get_next_by_FIELD() and get_previous_by_FIELD() don't crash when
        # microseconds values are stored in the database.
        Event.objects.create(when=datetime.datetime(2000, 1, 1, 16, 0, 0))
        Event.objects.create(when=datetime.datetime(2000, 1, 1, 6, 1, 1))
        Event.objects.create(when=datetime.datetime(2000, 1, 1, 13, 1, 1))
        e = Event.objects.create(when=datetime.datetime(2000, 1, 1, 12, 0, 20, 24))
        self.assertEqual(
            e.get_next_by_when().when, datetime.datetime(2000, 1, 1, 13, 1, 1)
        )
        self.assertEqual(
            e.get_previous_by_when().when, datetime.datetime(2000, 1, 1, 6, 1, 1)
        )

    def test_get_next_prev_by_field_unsaved(self):
        msg = 'get_next/get_previous cannot be used on unsaved objects.'
        with self.assertRaisesMessage(ValueError, msg):
            Event().get_next_by_when()
        with self.assertRaisesMessage(ValueError, msg):
            Event().get_previous_by_when()

    def test_primary_key_foreign_key_types(self):
        # Check Department and Worker (non-default PK type)
        d = Department.objects.create(id=10, name="IT")
        w = Worker.objects.create(department=d, name="Full-time")
        self.assertEqual(str(w), "Full-time")

    @skipUnlessDBFeature("supports_timezones")
    def test_timezones(self):
        # Saving an updating with timezone-aware datetime Python objects.
        # Regression test for #10443.
        # The idea is that all these creations and saving should work without
        # crashing. It's not rocket science.
        dt1 = datetime.datetime(2008, 8, 31, 16, 20, tzinfo=get_fixed_timezone(600))
        dt2 = datetime.datetime(2008, 8, 31, 17, 20, tzinfo=get_fixed_timezone(600))
        obj = Article.objects.create(
            headline="A headline", pub_date=dt1, article_text="foo"
        )
        obj.pub_date = dt2
        obj.save()
        self.assertEqual(
            Article.objects.filter(headline="A headline").update(pub_date=dt1),
            1
        )

    def test_chained_fks(self):
        """
        Regression for #18432: Chained foreign keys with to_field produce incorrect query
        """

        m1 = Model1.objects.create(pkey=1000)
        m2 = Model2.objects.create(model1=m1)
        m3 = Model3.objects.create(model2=m2)

        # this is the actual test for #18432
        m3 = Model3.objects.get(model2=1000)
        m3.model2


class ModelValidationTest(TestCase):
    def test_pk_validation(self):
        NonAutoPK.objects.create(name="one")
        again = NonAutoPK(name="one")
        with self.assertRaises(ValidationError):
            again.validate_unique()


class EvaluateMethodTest(TestCase):
    """
    Regression test for #13640: cannot filter by objects with 'evaluate' attr
    """

    def test_model_with_evaluate_method(self):
        """
        You can filter by objects that have an 'evaluate' attr
        """
        dept = Department.objects.create(pk=1, name='abc')
        dept.evaluate = 'abc'
        Worker.objects.filter(department=dept)
