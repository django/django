"""
Various combination queries that have been problematic in the past.
"""

from django.db import models
from django.db.models.query import Q

class Tag(models.Model):
    name = models.CharField(maxlength=10)
    parent = models.ForeignKey('self', blank=True, null=True)

    def __unicode__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(maxlength=10)
    num = models.IntegerField()

    def __unicode__(self):
        return self.name

class Item(models.Model):
    name = models.CharField(maxlength=10)
    data_ = models.CharField(maxlength=10, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    creator = models.ForeignKey(Author)

    def __unicode__(self):
        return self.name

class Report(models.Model):
    name = models.CharField(maxlength=10)
    creator = models.ForeignKey(Author, to_field='num')

    def __unicode__(self):
        return self.name


__test__ = {'API_TESTS':"""
>>> t1 = Tag(name='t1')
>>> t1.save()
>>> t2 = Tag(name='t2', parent=t1)
>>> t2.save()
>>> t3 = Tag(name='t3', parent=t1)
>>> t3.save()
>>> t4 = Tag(name='t4', parent=t3)
>>> t4.save()


>>> a1 = Author(name='a1', num=1001)
>>> a1.save()
>>> a2 = Author(name='a2', num=2002)
>>> a2.save()
>>> a3 = Author(name='a3', num=3003)
>>> a3.save()
>>> a4 = Author(name='a4', num=4004)
>>> a4.save()

>>> i1 = Item(name='one', creator=a1)
>>> i1.save()
>>> i1.tags = [t1, t2]
>>> i2 = Item(name='two', creator=a2)
>>> i2.save()
>>> i2.tags = [t1, t3]
>>> i3 = Item(name='three', data_='x', creator=a2)
>>> i3.save()
>>> i4 = Item(name='four', creator=a4)
>>> i4.save()
>>> i4.tags = [t4]

>>> r1 = Report(name='r1', creator=a1)
>>> r1.save()

Bug #1050
>>> Item.objects.filter(tags__isnull=True)
[<Item: three>]
>>> Item.objects.filter(tags__id__isnull=True)
[<Item: three>]

Bug #1801
>>> Author.objects.filter(item=i2)
[<Author: a2>]
>>> Author.objects.filter(item=i3)
[<Author: a2>]

# FIXME: When we join these queries, we MUST NOT share the table joins. this is
# the case for all m-to-m and 1-to-m joins (but m-to-1 is fine).
# >>> Author.objects.filter(item=i2) & Author.objects.filter(item=i3)
# [<Author: a2>]

Bug #2306
Checking that no join types are "left outer" joins.
>>> query = Item.objects.filter(tags=t2).query
>>> query.LOUTER not in [x[2][2] for x in query.alias_map.values()]
True

>>> Item.objects.filter(Q(tags=t1)).order_by('name')
[<Item: one>, <Item: two>]
>>> Item.objects.filter(Q(tags=t1) & Q(tags=t2))
[<Item: one>]
>>> Item.objects.filter(Q(tags=t1)).filter(Q(tags=t2))
[<Item: one>]

Bug #4464
>>> Item.objects.filter(tags=t1).filter(tags=t2)
[<Item: one>]
>>> Item.objects.filter(tags__in=[t1, t2]).distinct().order_by('name')
[<Item: one>, <Item: two>]
>>> Item.objects.filter(tags__in=[t1, t2]).filter(tags=t3)
[<Item: two>]

Bug #2080, #3592
>>> Author.objects.filter(Q(name='a3') | Q(item__name='one'))
[<Author: a1>, <Author: a3>]

Bug #2939
# FIXME: ValueQuerySets don't work yet.
# >>> Item.objects.values('creator').distinct().count()
# 2

Bug #2253
>>> q1 = Item.objects.order_by('name')
>>> q2 = Item.objects.filter(id=i1.id)
>>> q1
[<Item: four>, <Item: one>, <Item: three>, <Item: two>]
>>> q2
[<Item: one>]
>>> (q1 | q2).order_by('name')
[<Item: four>, <Item: one>, <Item: three>, <Item: two>]
>>> (q1 & q2).order_by('name')
[<Item: one>]

Bug #3265
# FIXME: Currently causes a crash. Probably not worth fixing, but must make it
# a validation error in that case.
# >>> Item.objects.get(data___exact='x')
# <Item: three>

Bugs #4088 & #4306
>>> Report.objects.filter(creator=1001)
[<Report: r1>]
>>> Report.objects.filter(creator__num=1001)
[<Report: r1>]

# FIXME: The "removing final pk comparison" optimization is biting us here.
# Need to only remove it if the join was also on the pk value.
# >>> Report.objects.filter(creator__id=1001)
# []
# >>> Report.objects.filter(creator__id=a1.id)
# [<Report: r1>]

>>> Report.objects.filter(creator__name='a1')
[<Report: r1>]

Bug #4510
>>> Author.objects.filter(report__name='r1')
[<Author: a1>]

Bug #5324
>>> Item.objects.filter(tags__name='t4')
[<Item: four>]

# FIXME: We seem to be constructing the right SQL here, but maybe a NULL test
# for the pk of Tag is needed or something?
# >>> Item.objects.exclude(tags__name='t4').order_by('name').distinct()
# [<Item: one>, <Item: three>, <Item: two>]

Bug #2091
>>> t = Tag.objects.get(name='t4')
>>> Item.objects.filter(tags__in=[t])
[<Item: four>]

Combining querysets built on different models should behave in a well-defined
fashion. We raise an error.
>>> Author.objects.all() & Tag.objects.all()
Traceback (most recent call last):
...
AssertionError: Cannot combine queries on two different base models.
>>> Author.objects.all() | Tag.objects.all()
Traceback (most recent call last):
...
AssertionError: Cannot combine queries on two different base models.

Bug #3141
>>> Author.objects.extra(select={'foo': '1'}).count()
4
"""}

