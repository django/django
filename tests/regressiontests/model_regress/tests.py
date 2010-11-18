import datetime
from operator import attrgetter

from django.test import TestCase, skipUnlessDBFeature
from django.utils import tzinfo

from models import (Worker, Article, Party, Event, Department,
    BrokenUnicodeMethod, NonAutoPK)



class ModelTests(TestCase):
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

    def test_empty_choice(self):
        # NOTE: Part of the regression test here is merely parsing the model
        # declaration. The verbose_name, in particular, did not always work.
        a = Article.objects.create(
            headline="Look at me!", pub_date=datetime.datetime.now()
        )
        # An empty choice field should return None for the display name.
        self.assertIs(a.get_status_display(), None)

        # Empty strings should be returned as Unicode
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(a.misc_data, u'')
        self.assertIs(type(a.misc_data), unicode)

    def test_long_textfield(self):
        # TextFields can hold more than 4000 characters (this was broken in
        # Oracle).
        a = Article.objects.create(
            headline="Really, really big",
            pub_date=datetime.datetime.now(),
            article_text = "ABCDE" * 1000
        )
        a = Article.objects.get(pk=a.pk)
        self.assertEqual
        (len(a.article_text), 5000)

    def test_date_lookup(self):
        # Regression test for #659
        Party.objects.create(when=datetime.datetime(1999, 12, 31))
        Party.objects.create(when=datetime.datetime(1998, 12, 31))
        Party.objects.create(when=datetime.datetime(1999, 1, 1))
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
            attrgetter("when")
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
            attrgetter("when")
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__month="12"), [
                datetime.date(1999, 12, 31),
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when")
        )
        self.assertQuerysetEqual(
            Party.objects.filter(when__year="1998"), [
                datetime.date(1998, 12, 31),
            ],
            attrgetter("when")
        )

    def test_date_filter_null(self):
        # Date filtering was failing with NULL date values in SQLite
        # (regression test for #3501, amongst other things).
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
        # Check that get_next_by_FIELD and get_previous_by_FIELD don't crash
        # when we have usecs values stored on the database
        #
        # It crashed after the Field.get_db_prep_* refactor, because on most
        # backends DateTimeFields supports usecs, but DateTimeField.to_python
        # didn't recognize them. (Note that
        # Model._get_next_or_previous_by_FIELD coerces values to strings)
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

    def test_primary_key_foreign_key_types(self):
        # Check Department and Worker (non-default PK type)
        d = Department.objects.create(id=10, name="IT")
        w = Worker.objects.create(department=d, name="Full-time")
        self.assertEqual(unicode(w), "Full-time")

    def test_broken_unicode(self):
        # Models with broken unicode methods should still have a printable repr
        b = BrokenUnicodeMethod.objects.create(name="Jerry")
        self.assertEqual(repr(b), "<BrokenUnicodeMethod: [Bad Unicode data]>")

    @skipUnlessDBFeature("supports_timezones")
    def test_timezones(self):
        # Saving an updating with timezone-aware datetime Python objects.
        # Regression test for #10443.
        # The idea is that all these creations and saving should work without
        # crashing. It's not rocket science.
        dt1 = datetime.datetime(2008, 8, 31, 16, 20, tzinfo=tzinfo.FixedOffset(600))
        dt2 = datetime.datetime(2008, 8, 31, 17, 20, tzinfo=tzinfo.FixedOffset(600))
        obj = Article.objects.create(
            headline="A headline", pub_date=dt1, article_text="foo"
        )
        obj.pub_date = dt2
        obj.save()
        self.assertEqual(
            Article.objects.filter(headline="A headline").update(pub_date=dt1),
            1
        )

class ModelValidationTest(TestCase):
    def test_pk_validation(self):
        one = NonAutoPK.objects.create(name="one")
        again = NonAutoPK(name="one")
        self.assertRaises(ValidationError, again.validate_unique)
