# coding: utf-8
import datetime

from django.conf import settings
from django.db import models
from django.utils import tzinfo

CHOICES = (
    (1, 'first'),
    (2, 'second'),
)

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()
    status = models.IntegerField(blank=True, null=True, choices=CHOICES)
    misc_data = models.CharField(max_length=100, blank=True)
    article_text = models.TextField()

    class Meta:
        ordering = ('pub_date','headline')
        # A utf-8 verbose name (Ångström's Articles) to test they are valid.
        verbose_name = "\xc3\x85ngstr\xc3\xb6m's Articles"

    def __unicode__(self):
        return self.headline

class Movie(models.Model):
    #5218: Test models with non-default primary keys / AutoFields
    movie_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)

class Party(models.Model):
    when = models.DateField(null=True)

class Event(models.Model):
    when = models.DateTimeField()

class Department(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class Worker(models.Model):
    department = models.ForeignKey(Department)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class BrokenUnicodeMethod(models.Model):
    name = models.CharField(max_length=7)

    def __unicode__(self):
        # Intentionally broken (trying to insert a unicode value into a str
        # object).
        return 'Názov: %s' % self.name


__test__ = {'API_TESTS': """
(NOTE: Part of the regression test here is merely parsing the model
declaration. The verbose_name, in particular, did not always work.)

An empty choice field should return None for the display name.

>>> from datetime import datetime
>>> a = Article(headline="Look at me!", pub_date=datetime.now())
>>> a.save()
>>> a.get_status_display() is None
True

Empty strings should be returned as Unicode
>>> a2 = Article.objects.get(pk=a.id)
>>> a2.misc_data
u''

# TextFields can hold more than 4000 characters (this was broken in Oracle).
>>> a3 = Article(headline="Really, really big", pub_date=datetime.now())
>>> a3.article_text = "ABCDE" * 1000
>>> a3.save()
>>> a4 = Article.objects.get(pk=a3.id)
>>> len(a4.article_text)
5000

# Regression test for #659
>>> import datetime
>>> p = Party.objects.create(when = datetime.datetime(1999, 12, 31))
>>> p = Party.objects.create(when = datetime.datetime(1998, 12, 31))
>>> p = Party.objects.create(when = datetime.datetime(1999, 1, 1))
>>> [p.when for p in Party.objects.filter(when__month=2)]
[]
>>> [p.when for p in Party.objects.filter(when__month=1)]
[datetime.date(1999, 1, 1)]
>>> [p.when for p in Party.objects.filter(when__month=12)]
[datetime.date(1999, 12, 31), datetime.date(1998, 12, 31)]
>>> [p.when for p in Party.objects.filter(when__year=1998)]
[datetime.date(1998, 12, 31)]

# Regression test for #8510
>>> [p.when for p in Party.objects.filter(when__day='31')]
[datetime.date(1999, 12, 31), datetime.date(1998, 12, 31)]
>>> [p.when for p in Party.objects.filter(when__month='12')]
[datetime.date(1999, 12, 31), datetime.date(1998, 12, 31)]
>>> [p.when for p in Party.objects.filter(when__year='1998')]
[datetime.date(1998, 12, 31)]

# Date filtering was failing with NULL date values in SQLite (regression test
# for #3501, amongst other things).
>>> _ = Party.objects.create()
>>> p = Party.objects.filter(when__month=1)[0]
>>> p.when
datetime.date(1999, 1, 1)
>>> l = Party.objects.filter(pk=p.pk).dates("when", "month")
>>> l[0].month == 1
True

# Check that get_next_by_FIELD and get_previous_by_FIELD don't crash when we
# have usecs values stored on the database
#
# [It crashed after the Field.get_db_prep_* refactor, because on most backends
#  DateTimeFields supports usecs, but DateTimeField.to_python didn't recognize
#  them. (Note that Model._get_next_or_previous_by_FIELD coerces values to
#  strings)]
#
>>> e = Event.objects.create(when = datetime.datetime(2000, 1, 1, 16, 0, 0))
>>> e = Event.objects.create(when = datetime.datetime(2000, 1, 1, 6, 1, 1))
>>> e = Event.objects.create(when = datetime.datetime(2000, 1, 1, 13, 1, 1))
>>> e = Event.objects.create(when = datetime.datetime(2000, 1, 1, 12, 0, 20, 24))
>>> e.get_next_by_when().when
datetime.datetime(2000, 1, 1, 13, 1, 1)
>>> e.get_previous_by_when().when
datetime.datetime(2000, 1, 1, 6, 1, 1)

# Check Department and Worker
>>> d = Department(id=10, name='IT')
>>> d.save()
>>> w = Worker(department=d, name='Full-time')
>>> w.save()
>>> w
<Worker: Full-time>

# Models with broken unicode methods should still have a printable repr
>>> b = BrokenUnicodeMethod(name="Jerry")
>>> b.save()
>>> BrokenUnicodeMethod.objects.all()
[<BrokenUnicodeMethod: [Bad Unicode data]>]

"""}

if settings.DATABASE_ENGINE not in ("mysql", "oracle"):
    __test__["timezone-tests"] = """
# Saving an updating with timezone-aware datetime Python objects. Regression
# test for #10443.

# The idea is that all these creations and saving should work without crashing.
# It's not rocket science.
>>> Article.objects.all().delete()
>>> dt1 = datetime.datetime(2008, 8, 31, 16, 20, tzinfo=tzinfo.FixedOffset(600))
>>> dt2 = datetime.datetime(2008, 8, 31, 17, 20, tzinfo=tzinfo.FixedOffset(600))
>>> obj = Article.objects.create(headline="A headline", pub_date=dt1, article_text="foo")

>>> obj.pub_date = dt2
>>> obj.save()
>>> Article.objects.filter(headline="A headline").update(pub_date=dt1)
1

"""

