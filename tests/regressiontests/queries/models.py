"""
Various complex queries that have been problematic in the past.
"""

from django.db import models
from django.db.models.query import Q

class Tag(models.Model):
    name = models.CharField(maxlength=10)
    parent = models.ForeignKey('self', blank=True, null=True)

    def __unicode__(self):
        return self.name

class Note(models.Model):
    note = models.CharField(maxlength=100)

    class Meta:
        ordering = ['note']

    def __unicode__(self):
        return self.note

class ExtraInfo(models.Model):
    info = models.CharField(maxlength=100)
    note = models.ForeignKey(Note)

    class Meta:
        ordering = ['info']

    def __unicode__(self):
        return self.info

class Author(models.Model):
    name = models.CharField(maxlength=10)
    num = models.IntegerField(unique=True)
    extra = models.ForeignKey(ExtraInfo)

    def __unicode__(self):
        return self.name

class Item(models.Model):
    name = models.CharField(maxlength=10)
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    creator = models.ForeignKey(Author)
    note = models.ForeignKey(Note)

    class Meta:
        ordering = ['-note', 'name']

    def __unicode__(self):
        return self.name

class Report(models.Model):
    name = models.CharField(maxlength=10)
    creator = models.ForeignKey(Author, to_field='num')

    def __unicode__(self):
        return self.name

class Ranking(models.Model):
    rank = models.IntegerField()
    author = models.ForeignKey(Author)

    class Meta:
        # A complex ordering specification. Should stress the system a bit.
        ordering = ('author__extra__note', 'author__name', 'rank')

    def __unicode__(self):
        return '%d: %s' % (self.rank, self.author.name)

class Cover(models.Model):
    title = models.CharField(maxlength=50)
    item = models.ForeignKey(Item)

    class Meta:
        ordering = ['item']

    def __unicode__(self):
        return self.title

__test__ = {'API_TESTS':"""
>>> t1 = Tag(name='t1')
>>> t1.save()
>>> t2 = Tag(name='t2', parent=t1)
>>> t2.save()
>>> t3 = Tag(name='t3', parent=t1)
>>> t3.save()
>>> t4 = Tag(name='t4', parent=t3)
>>> t4.save()
>>> t5 = Tag(name='t5', parent=t3)
>>> t5.save()

>>> n1 = Note(note='n1')
>>> n1.save()
>>> n2 = Note(note='n2')
>>> n2.save()
>>> n3 = Note(note='n3')
>>> n3.save()

Create these out of order so that sorting by 'id' will be different to sorting
by 'info'. Helps detect some problems later.
>>> e2 = ExtraInfo(info='e2', note=n2)
>>> e2.save()
>>> e1 = ExtraInfo(info='e1', note=n1)
>>> e1.save()

>>> a1 = Author(name='a1', num=1001, extra=e1)
>>> a1.save()
>>> a2 = Author(name='a2', num=2002, extra=e1)
>>> a2.save()
>>> a3 = Author(name='a3', num=3003, extra=e2)
>>> a3.save()
>>> a4 = Author(name='a4', num=4004, extra=e2)
>>> a4.save()

>>> i1 = Item(name='one', creator=a1, note=n3)
>>> i1.save()
>>> i1.tags = [t1, t2]
>>> i2 = Item(name='two', creator=a2, note=n2)
>>> i2.save()
>>> i2.tags = [t1, t3]
>>> i3 = Item(name='three', creator=a2, note=n3)
>>> i3.save()
>>> i4 = Item(name='four', creator=a4, note=n3)
>>> i4.save()
>>> i4.tags = [t4]

>>> r1 = Report(name='r1', creator=a1)
>>> r1.save()
>>> r2 = Report(name='r2', creator=a3)
>>> r2.save()

Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the Meta.ordering
will be rank3, rank2, rank1.
>>> rank1 = Ranking(rank=2, author=a2)
>>> rank1.save()
>>> rank2 = Ranking(rank=1, author=a3)
>>> rank2.save()
>>> rank3 = Ranking(rank=3, author=a1)
>>> rank3.save()

>>> c1 = Cover(title="first", item=i4)
>>> c1.save()
>>> c2 = Cover(title="second", item=i2)
>>> c2.save()

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
>>> Author.objects.filter(item=i2) & Author.objects.filter(item=i3)
[<Author: a2>]

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

Bug #1878, #2939
>>> Item.objects.values('creator').distinct().count()
3

# Create something with a duplicate 'name' so that we can test multi-column
# cases (which require some tricky SQL transformations under the covers).
>>> xx = Item(name='four', creator=a2, note=n1)
>>> xx.save()
>>> Item.objects.exclude(name='two').values('creator', 'name').distinct().count()
4
>>> xx.delete()

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

Bugs #4088, #4306
>>> Report.objects.filter(creator=1001)
[<Report: r1>]
>>> Report.objects.filter(creator__num=1001)
[<Report: r1>]
>>> Report.objects.filter(creator__id=1001)
[]
>>> Report.objects.filter(creator__id=a1.id)
[<Report: r1>]
>>> Report.objects.filter(creator__name='a1')
[<Report: r1>]

Bug #4510
>>> Author.objects.filter(report__name='r1')
[<Author: a1>]

Bug #5324
>>> Item.objects.filter(tags__name='t4')
[<Item: four>]
>>> Item.objects.exclude(tags__name='t4').order_by('name').distinct()
[<Item: one>, <Item: three>, <Item: two>]
>>> Author.objects.exclude(item__name='one').distinct().order_by('name')
[<Author: a2>, <Author: a3>, <Author: a4>]

# Excluding from a relation that cannot be NULL should not use outer joins.
>>> query = Item.objects.exclude(creator__in=[a1, a2]).query
>>> query.LOUTER not in [x[2][2] for x in query.alias_map.values()]
True

# When only one of the joins is nullable (here, the Author -> Item join), we
# should only get outer joins after that point (one, in this case). We also
# show that three tables (so, two joins) are involved.
>>> qs = Report.objects.exclude(creator__item__name='one')
>>> list(qs)
[<Report: r2>]
>>> len([x[2][2] for x in qs.query.alias_map.values() if x[2][2] == query.LOUTER])
1
>>> len(qs.query.alias_map)
3

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

Bug #2400
>>> Author.objects.filter(item__isnull=True)
[<Author: a3>]
>>> Tag.objects.filter(item__isnull=True)
[<Tag: t5>]

Bug #2496
>>> Item.objects.extra(tables=['queries_author']).select_related().order_by('name')[:1]
[<Item: four>]

Bug #2076
# Ordering on related tables should be possible, even if the table is not
# otherwise involved.
>>> Item.objects.order_by('note__note', 'name')
[<Item: two>, <Item: four>, <Item: one>, <Item: three>]

# Ordering on a related field should use the remote model's default ordering as
# a final step.
>>> Author.objects.order_by('extra', '-name')
[<Author: a2>, <Author: a1>, <Author: a4>, <Author: a3>]

# Using remote model default ordering can span multiple models (in this case,
# Cover is ordered by Item's default, which uses Note's default).
>>> Cover.objects.all()
[<Cover: first>, <Cover: second>]

# If the remote model does not have a default ordering, we order by its 'id'
# field.
>>> Item.objects.order_by('creator', 'name')
[<Item: one>, <Item: three>, <Item: two>, <Item: four>]

# Cross model ordering is possible in Meta, too.
>>> Ranking.objects.all()
[<Ranking: 3: a1>, <Ranking: 2: a2>, <Ranking: 1: a3>]
>>> Ranking.objects.all().order_by('rank')
[<Ranking: 1: a3>, <Ranking: 2: a2>, <Ranking: 3: a1>]

# Ordering of extra() pieces is possible, too and you can mix extra fields and
# model fields in the ordering.
>>> Ranking.objects.extra(tables=['django_site'], order_by=['-django_site.id', 'rank'])
[<Ranking: 1: a3>, <Ranking: 2: a2>, <Ranking: 3: a1>]

>>> qs = Ranking.objects.extra(select={'good': 'rank > 2'})
>>> [o.good for o in qs.extra(order_by=('-good',))] == [True, False, False]
True
>>> qs.extra(order_by=('-good', 'id'))
[<Ranking: 3: a1>, <Ranking: 2: a2>, <Ranking: 1: a3>]

Bugs #2874, #3002
>>> qs = Item.objects.select_related().order_by('note__note', 'name')
>>> list(qs)
[<Item: two>, <Item: four>, <Item: one>, <Item: three>]

# This is also a good select_related() test because there are multiple Note
# entries in the SQL. The two Note items should be different.
>>> qs[0].note, qs[0].creator.extra.note
(<Note: n2>, <Note: n1>)
"""}

