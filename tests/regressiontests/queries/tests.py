import datetime
import pickle
import sys
import unittest

from django.conf import settings
from django.core.exceptions import FieldError
from django.db import DatabaseError, connection, connections, DEFAULT_DB_ALIAS
from django.db.models import Count
from django.db.models.query import Q, ITER_CHUNK_SIZE, EmptyQuerySet
from django.test import TestCase
from django.utils.datastructures import SortedDict

from models import (Annotation, Article, Author, Celebrity, Child, Cover, Detail,
    DumbCategory, ExtraInfo, Fan, Item, LeafA, LoopX, LoopZ, ManagedModel,
    Member, NamedCategory, Note, Number, Plaything, PointerA, Ranking, Related,
    Report, ReservedName, Tag, TvChef, Valid, X, Food, Eaten, Node)


class BaseQuerysetTest(TestCase):
    def assertValueQuerysetEqual(self, qs, values):
        return self.assertQuerysetEqual(qs, values, transform=lambda x: x)

    def assertRaisesMessage(self, exc, msg, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, e:
            self.assertEqual(msg, str(e))
            self.assertTrue(isinstance(e, exc), "Expected %s, got %s" % (exc, type(e)))
        else:
            if hasattr(exc, '__name__'):
                excName = exc.__name__
            else:
                excName = str(exc)
            raise AssertionError, "%s not raised" % excName


class Queries1Tests(BaseQuerysetTest):
    def setUp(self):
        generic = NamedCategory.objects.create(name="Generic")
        self.t1 = Tag.objects.create(name='t1', category=generic)
        self.t2 = Tag.objects.create(name='t2', parent=self.t1, category=generic)
        self.t3 = Tag.objects.create(name='t3', parent=self.t1)
        t4 = Tag.objects.create(name='t4', parent=self.t3)
        self.t5 = Tag.objects.create(name='t5', parent=self.t3)

        self.n1 = Note.objects.create(note='n1', misc='foo', id=1)
        n2 = Note.objects.create(note='n2', misc='bar', id=2)
        self.n3 = Note.objects.create(note='n3', misc='foo', id=3)

        ann1 = Annotation.objects.create(name='a1', tag=self.t1)
        ann1.notes.add(self.n1)
        ann2 = Annotation.objects.create(name='a2', tag=t4)
        ann2.notes.add(n2, self.n3)

        # Create these out of order so that sorting by 'id' will be different to sorting
        # by 'info'. Helps detect some problems later.
        self.e2 = ExtraInfo.objects.create(info='e2', note=n2)
        e1 = ExtraInfo.objects.create(info='e1', note=self.n1)

        self.a1 = Author.objects.create(name='a1', num=1001, extra=e1)
        self.a2 = Author.objects.create(name='a2', num=2002, extra=e1)
        a3 = Author.objects.create(name='a3', num=3003, extra=self.e2)
        self.a4 = Author.objects.create(name='a4', num=4004, extra=self.e2)

        self.time1 = datetime.datetime(2007, 12, 19, 22, 25, 0)
        self.time2 = datetime.datetime(2007, 12, 19, 21, 0, 0)
        time3 = datetime.datetime(2007, 12, 20, 22, 25, 0)
        time4 = datetime.datetime(2007, 12, 20, 21, 0, 0)
        self.i1 = Item.objects.create(name='one', created=self.time1, modified=self.time1, creator=self.a1, note=self.n3)
        self.i1.tags = [self.t1, self.t2]
        self.i2 = Item.objects.create(name='two', created=self.time2, creator=self.a2, note=n2)
        self.i2.tags = [self.t1, self.t3]
        self.i3 = Item.objects.create(name='three', created=time3, creator=self.a2, note=self.n3)
        i4 = Item.objects.create(name='four', created=time4, creator=self.a4, note=self.n3)
        i4.tags = [t4]

        self.r1 = Report.objects.create(name='r1', creator=self.a1)
        Report.objects.create(name='r2', creator=a3)
        Report.objects.create(name='r3')

        # Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the Meta.ordering
        # will be rank3, rank2, rank1.
        self.rank1 = Ranking.objects.create(rank=2, author=self.a2)

        Cover.objects.create(title="first", item=i4)
        Cover.objects.create(title="second", item=self.i2)

    def test_ticket1050(self):
        self.assertQuerysetEqual(
            Item.objects.filter(tags__isnull=True),
            ['<Item: three>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(tags__id__isnull=True),
            ['<Item: three>']
        )

    def test_ticket1801(self):
        self.assertQuerysetEqual(
            Author.objects.filter(item=self.i2),
            ['<Author: a2>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(item=self.i3),
            ['<Author: a2>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(item=self.i2) & Author.objects.filter(item=self.i3),
            ['<Author: a2>']
        )

    def test_ticket2306(self):
        # Checking that no join types are "left outer" joins.
        query = Item.objects.filter(tags=self.t2).query
        self.assertTrue(query.LOUTER not in [x[2] for x in query.alias_map.values()])

        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags=self.t1)).order_by('name'),
            ['<Item: one>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags=self.t1)).filter(Q(tags=self.t2)),
            ['<Item: one>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags=self.t1)).filter(Q(creator__name='fred')|Q(tags=self.t2)),
            ['<Item: one>']
        )

        # Each filter call is processed "at once" against a single table, so this is
        # different from the previous example as it tries to find tags that are two
        # things at once (rather than two tags).
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags=self.t1) & Q(tags=self.t2)),
            []
        )
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags=self.t1), Q(creator__name='fred')|Q(tags=self.t2)),
            []
        )

        qs = Author.objects.filter(ranking__rank=2, ranking__id=self.rank1.id)
        self.assertQuerysetEqual(list(qs), ['<Author: a2>'])
        self.assertEqual(2, qs.query.count_active_tables(), 2)
        qs = Author.objects.filter(ranking__rank=2).filter(ranking__id=self.rank1.id)
        self.assertEqual(qs.query.count_active_tables(), 3)

    def test_ticket4464(self):
        self.assertQuerysetEqual(
            Item.objects.filter(tags=self.t1).filter(tags=self.t2),
            ['<Item: one>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).distinct().order_by('name'),
            ['<Item: one>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).filter(tags=self.t3),
            ['<Item: two>']
        )

        # Make sure .distinct() works with slicing (this was broken in Oracle).
        self.assertQuerysetEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).order_by('name')[:3],
            ['<Item: one>', '<Item: one>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).distinct().order_by('name')[:3],
            ['<Item: one>', '<Item: two>']
        )

    def test_tickets_2080_3592(self):
        self.assertQuerysetEqual(
            Author.objects.filter(item__name='one') | Author.objects.filter(name='a3'),
            ['<Author: a1>', '<Author: a3>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(Q(item__name='one') | Q(name='a3')),
            ['<Author: a1>', '<Author: a3>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(Q(name='a3') | Q(item__name='one')),
            ['<Author: a1>', '<Author: a3>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(Q(item__name='three') | Q(report__name='r3')),
            ['<Author: a2>']
        )

    def test_ticket6074(self):
        # Merging two empty result sets shouldn't leave a queryset with no constraints
        # (which would match everything).
        self.assertQuerysetEqual(Author.objects.filter(Q(id__in=[])), [])
        self.assertQuerysetEqual(
            Author.objects.filter(Q(id__in=[])|Q(id__in=[])),
            []
        )

    def test_tickets_1878_2939(self):
        self.assertEqual(Item.objects.values('creator').distinct().count(), 3)

        # Create something with a duplicate 'name' so that we can test multi-column
        # cases (which require some tricky SQL transformations under the covers).
        xx = Item(name='four', created=self.time1, creator=self.a2, note=self.n1)
        xx.save()
        self.assertEqual(
            Item.objects.exclude(name='two').values('creator', 'name').distinct().count(),
            4
        )
        self.assertEqual(
            Item.objects.exclude(name='two').extra(select={'foo': '%s'}, select_params=(1,)).values('creator', 'name', 'foo').distinct().count(),
            4
        )
        self.assertEqual(
            Item.objects.exclude(name='two').extra(select={'foo': '%s'}, select_params=(1,)).values('creator', 'name').distinct().count(),
            4
        )
        xx.delete()

    def test_ticket7323(self):
        self.assertEqual(Item.objects.values('creator', 'name').count(), 4)

    def test_ticket2253(self):
        q1 = Item.objects.order_by('name')
        q2 = Item.objects.filter(id=self.i1.id)
        self.assertQuerysetEqual(
            q1,
            ['<Item: four>', '<Item: one>', '<Item: three>', '<Item: two>']
        )
        self.assertQuerysetEqual(q2, ['<Item: one>'])
        self.assertQuerysetEqual(
            (q1 | q2).order_by('name'),
            ['<Item: four>', '<Item: one>', '<Item: three>', '<Item: two>']
        )
        self.assertQuerysetEqual((q1 & q2).order_by('name'), ['<Item: one>'])

        # FIXME: This is difficult to fix and very much an edge case, so punt for now.
        # This is related to the order_by() tests, below, but the old bug exhibited
        # itself here (q2 was pulling too many tables into the combined query with the
        # new ordering, but only because we have evaluated q2 already).
        #
        #self.assertEqual(len((q1 & q2).order_by('name').query.tables), 1)

        q1 = Item.objects.filter(tags=self.t1)
        q2 = Item.objects.filter(note=self.n3, tags=self.t2)
        q3 = Item.objects.filter(creator=self.a4)
        self.assertQuerysetEqual(
            ((q1 & q2) | q3).order_by('name'),
            ['<Item: four>', '<Item: one>']
        )

    def test_tickets_4088_4306(self):
        self.assertQuerysetEqual(
            Report.objects.filter(creator=1001),
            ['<Report: r1>']
        )
        self.assertQuerysetEqual(
            Report.objects.filter(creator__num=1001),
            ['<Report: r1>']
        )
        self.assertQuerysetEqual(Report.objects.filter(creator__id=1001), [])
        self.assertQuerysetEqual(
            Report.objects.filter(creator__id=self.a1.id),
            ['<Report: r1>']
        )
        self.assertQuerysetEqual(
            Report.objects.filter(creator__name='a1'),
            ['<Report: r1>']
        )

    def test_ticket4510(self):
        self.assertQuerysetEqual(
            Author.objects.filter(report__name='r1'),
            ['<Author: a1>']
        )

    def test_ticket7378(self):
        self.assertQuerysetEqual(self.a1.report_set.all(), ['<Report: r1>'])

    def test_tickets_5324_6704(self):
        self.assertQuerysetEqual(
            Item.objects.filter(tags__name='t4'),
            ['<Item: four>']
        )
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t4').order_by('name').distinct(),
            ['<Item: one>', '<Item: three>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t4').order_by('name').distinct().reverse(),
            ['<Item: two>', '<Item: three>', '<Item: one>']
        )
        self.assertQuerysetEqual(
            Author.objects.exclude(item__name='one').distinct().order_by('name'),
            ['<Author: a2>', '<Author: a3>', '<Author: a4>']
        )

        # Excluding across a m2m relation when there is more than one related
        # object associated was problematic.
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t1').order_by('name'),
            ['<Item: four>', '<Item: three>']
        )
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t1').exclude(tags__name='t4'),
            ['<Item: three>']
        )

        # Excluding from a relation that cannot be NULL should not use outer joins.
        query = Item.objects.exclude(creator__in=[self.a1, self.a2]).query
        self.assertTrue(query.LOUTER not in [x[2] for x in query.alias_map.values()])

        # Similarly, when one of the joins cannot possibly, ever, involve NULL
        # values (Author -> ExtraInfo, in the following), it should never be
        # promoted to a left outer join. So the following query should only
        # involve one "left outer" join (Author -> Item is 0-to-many).
        qs = Author.objects.filter(id=self.a1.id).filter(Q(extra__note=self.n1)|Q(item__note=self.n3))
        self.assertEqual(
            len([x[2] for x in qs.query.alias_map.values() if x[2] == query.LOUTER and qs.query.alias_refcount[x[1]]]),
            1
        )

        # The previous changes shouldn't affect nullable foreign key joins.
        self.assertQuerysetEqual(
            Tag.objects.filter(parent__isnull=True).order_by('name'),
            ['<Tag: t1>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(parent__isnull=True).order_by('name'),
            ['<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(Q(parent__name='t1') | Q(parent__isnull=True)).order_by('name'),
            ['<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(Q(parent__isnull=True) | Q(parent__name='t1')).order_by('name'),
            ['<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(Q(parent__parent__isnull=True)).order_by('name'),
            ['<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Tag.objects.filter(~Q(parent__parent__isnull=True)).order_by('name'),
            ['<Tag: t4>', '<Tag: t5>']
        )

    def test_ticket2091(self):
        t = Tag.objects.get(name='t4')
        self.assertQuerysetEqual(
            Item.objects.filter(tags__in=[t]),
            ['<Item: four>']
        )

    def test_heterogeneous_qs_combination(self):
        # Combining querysets built on different models should behave in a well-defined
        # fashion. We raise an error.
        self.assertRaisesMessage(
            AssertionError,
            'Cannot combine queries on two different base models.',
            lambda: Author.objects.all() & Tag.objects.all()
        )
        self.assertRaisesMessage(
            AssertionError,
            'Cannot combine queries on two different base models.',
            lambda: Author.objects.all() | Tag.objects.all()
        )

    def test_ticket3141(self):
        self.assertEqual(Author.objects.extra(select={'foo': '1'}).count(), 4)
        self.assertEqual(
            Author.objects.extra(select={'foo': '%s'}, select_params=(1,)).count(),
            4
        )

    def test_ticket2400(self):
        self.assertQuerysetEqual(
            Author.objects.filter(item__isnull=True),
            ['<Author: a3>']
        )
        self.assertQuerysetEqual(
            Tag.objects.filter(item__isnull=True),
            ['<Tag: t5>']
        )

    def test_ticket2496(self):
        self.assertQuerysetEqual(
            Item.objects.extra(tables=['queries_author']).select_related().order_by('name')[:1],
            ['<Item: four>']
        )

    def test_tickets_2076_7256(self):
        # Ordering on related tables should be possible, even if the table is
        # not otherwise involved.
        self.assertQuerysetEqual(
            Item.objects.order_by('note__note', 'name'),
            ['<Item: two>', '<Item: four>', '<Item: one>', '<Item: three>']
        )

        # Ordering on a related field should use the remote model's default
        # ordering as a final step.
        self.assertQuerysetEqual(
            Author.objects.order_by('extra', '-name'),
            ['<Author: a2>', '<Author: a1>', '<Author: a4>', '<Author: a3>']
        )

        # Using remote model default ordering can span multiple models (in this
        # case, Cover is ordered by Item's default, which uses Note's default).
        self.assertQuerysetEqual(
            Cover.objects.all(),
            ['<Cover: first>', '<Cover: second>']
        )

        # If the remote model does not have a default ordering, we order by its 'id'
        # field.
        self.assertQuerysetEqual(
            Item.objects.order_by('creator', 'name'),
            ['<Item: one>', '<Item: three>', '<Item: two>', '<Item: four>']
        )

        # Ordering by a many-valued attribute (e.g. a many-to-many or reverse
        # ForeignKey) is legal, but the results might not make sense. That
        # isn't Django's problem. Garbage in, garbage out.
        self.assertQuerysetEqual(
            Item.objects.filter(tags__isnull=False).order_by('tags', 'id'),
            ['<Item: one>', '<Item: two>', '<Item: one>', '<Item: two>', '<Item: four>']
        )

        # If we replace the default ordering, Django adjusts the required
        # tables automatically. Item normally requires a join with Note to do
        # the default ordering, but that isn't needed here.
        qs = Item.objects.order_by('name')
        self.assertQuerysetEqual(
            qs,
            ['<Item: four>', '<Item: one>', '<Item: three>', '<Item: two>']
        )
        self.assertEqual(len(qs.query.tables), 1)

    def test_tickets_2874_3002(self):
        qs = Item.objects.select_related().order_by('note__note', 'name')
        self.assertQuerysetEqual(
            qs,
            ['<Item: two>', '<Item: four>', '<Item: one>', '<Item: three>']
        )

        # This is also a good select_related() test because there are multiple
        # Note entries in the SQL. The two Note items should be different.
        self.assertTrue(repr(qs[0].note), '<Note: n2>')
        self.assertEqual(repr(qs[0].creator.extra.note), '<Note: n1>')

    def test_ticket3037(self):
        self.assertQuerysetEqual(
            Item.objects.filter(Q(creator__name='a3', name='two')|Q(creator__name='a4', name='four')),
            ['<Item: four>']
        )

    def test_tickets_5321_7070(self):
        # Ordering columns must be included in the output columns. Note that
        # this means results that might otherwise be distinct are not (if there
        # are multiple values in the ordering cols), as in this example. This
        # isn't a bug; it's a warning to be careful with the selection of
        # ordering columns.
        self.assertValueQuerysetEqual(
            Note.objects.values('misc').distinct().order_by('note', '-misc'),
            [{'misc': u'foo'}, {'misc': u'bar'}, {'misc': u'foo'}]
        )

    def test_ticket4358(self):
        # If you don't pass any fields to values(), relation fields are
        # returned as "foo_id" keys, not "foo". For consistency, you should be
        # able to pass "foo_id" in the fields list and have it work, too. We
        # actually allow both "foo" and "foo_id".

        # The *_id version is returned by default.
        self.assertTrue('note_id' in ExtraInfo.objects.values()[0])

        # You can also pass it in explicitly.
        self.assertValueQuerysetEqual(
            ExtraInfo.objects.values('note_id'),
            [{'note_id': 1}, {'note_id': 2}]
        )

        # ...or use the field name.
        self.assertValueQuerysetEqual(
            ExtraInfo.objects.values('note'),
            [{'note': 1}, {'note': 2}]
        )

    def test_ticket2902(self):
        # Parameters can be given to extra_select, *if* you use a SortedDict.

        # (First we need to know which order the keys fall in "naturally" on
        # your system, so we can put things in the wrong way around from
        # normal. A normal dict would thus fail.)
        s = [('a', '%s'), ('b', '%s')]
        params = ['one', 'two']
        if {'a': 1, 'b': 2}.keys() == ['a', 'b']:
            s.reverse()
            params.reverse()

        # This slightly odd comparison works around the fact that PostgreSQL will
        # return 'one' and 'two' as strings, not Unicode objects. It's a side-effect of
        # using constants here and not a real concern.
        d = Item.objects.extra(select=SortedDict(s), select_params=params).values('a', 'b')[0]
        self.assertEqual(d, {'a': u'one', 'b': u'two'})

        # Order by the number of tags attached to an item.
        l = Item.objects.extra(select={'count': 'select count(*) from queries_item_tags where queries_item_tags.item_id = queries_item.id'}).order_by('-count')
        self.assertEqual([o.count for o in l], [2, 2, 1, 0])

    def test_ticket6154(self):
        # Multiple filter statements are joined using "AND" all the time.

        self.assertQuerysetEqual(
            Author.objects.filter(id=self.a1.id).filter(Q(extra__note=self.n1)|Q(item__note=self.n3)),
            ['<Author: a1>']
        )
        self.assertQuerysetEqual(
                Author.objects.filter(Q(extra__note=self.n1)|Q(item__note=self.n3)).filter(id=self.a1.id),
            ['<Author: a1>']
        )

    def test_ticket6981(self):
        self.assertQuerysetEqual(
            Tag.objects.select_related('parent').order_by('name'),
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>']
        )

    def test_ticket9926(self):
        self.assertQuerysetEqual(
            Tag.objects.select_related("parent", "category").order_by('name'),
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Tag.objects.select_related('parent', "parent__category").order_by('name'),
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>']
        )

    def test_tickets_6180_6203(self):
        # Dates with limits and/or counts
        self.assertEqual(Item.objects.count(), 4)
        self.assertEqual(Item.objects.dates('created', 'month').count(), 1)
        self.assertEqual(Item.objects.dates('created', 'day').count(), 2)
        self.assertEqual(len(Item.objects.dates('created', 'day')), 2)
        self.assertEqual(Item.objects.dates('created', 'day')[0], datetime.datetime(2007, 12, 19, 0, 0))

    def test_tickets_7087_12242(self):
        # Dates with extra select columns
        self.assertQuerysetEqual(
            Item.objects.dates('created', 'day').extra(select={'a': 1}),
            ['datetime.datetime(2007, 12, 19, 0, 0)', 'datetime.datetime(2007, 12, 20, 0, 0)']
        )
        self.assertQuerysetEqual(
            Item.objects.extra(select={'a': 1}).dates('created', 'day'),
            ['datetime.datetime(2007, 12, 19, 0, 0)', 'datetime.datetime(2007, 12, 20, 0, 0)']
        )

        name="one"
        self.assertQuerysetEqual(
            Item.objects.dates('created', 'day').extra(where=['name=%s'], params=[name]),
            ['datetime.datetime(2007, 12, 19, 0, 0)']
        )

        self.assertQuerysetEqual(
            Item.objects.extra(where=['name=%s'], params=[name]).dates('created', 'day'),
            ['datetime.datetime(2007, 12, 19, 0, 0)']
        )

    def test_ticket7155(self):
        # Nullable dates
        self.assertQuerysetEqual(
            Item.objects.dates('modified', 'day'),
            ['datetime.datetime(2007, 12, 19, 0, 0)']
        )

    def test_ticket7098(self):
        # Make sure semi-deprecated ordering by related models syntax still
        # works.
        self.assertValueQuerysetEqual(
            Item.objects.values('note__note').order_by('queries_note.note', 'id'),
            [{'note__note': u'n2'}, {'note__note': u'n3'}, {'note__note': u'n3'}, {'note__note': u'n3'}]
        )

    def test_ticket7096(self):
        # Make sure exclude() with multiple conditions continues to work.
        self.assertQuerysetEqual(
            Tag.objects.filter(parent=self.t1, name='t3').order_by('name'),
            ['<Tag: t3>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(parent=self.t1, name='t3').order_by('name'),
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t4>', '<Tag: t5>']
        )
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t1', name='one').order_by('name').distinct(),
            ['<Item: four>', '<Item: three>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(name__in=['three', 'four']).exclude(tags__name='t1').order_by('name'),
            ['<Item: four>', '<Item: three>']
        )

        # More twisted cases, involving nested negations.
        self.assertQuerysetEqual(
            Item.objects.exclude(~Q(tags__name='t1', name='one')),
            ['<Item: one>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(~Q(tags__name='t1', name='one'), name='two'),
            ['<Item: two>']
        )
        self.assertQuerysetEqual(
            Item.objects.exclude(~Q(tags__name='t1', name='one'), name='two'),
            ['<Item: four>', '<Item: one>', '<Item: three>']
        )

    def test_tickets_7204_7506(self):
        # Make sure querysets with related fields can be pickled. If this
        # doesn't crash, it's a Good Thing.
        pickle.dumps(Item.objects.all())

    def test_ticket7813(self):
        # We should also be able to pickle things that use select_related().
        # The only tricky thing here is to ensure that we do the related
        # selections properly after unpickling.
        qs = Item.objects.select_related()
        query = qs.query.get_compiler(qs.db).as_sql()[0]
        query2 = pickle.loads(pickle.dumps(qs.query))
        self.assertEqual(
            query2.get_compiler(qs.db).as_sql()[0],
            query
        )

    def test_deferred_load_qs_pickling(self):
        # Check pickling of deferred-loading querysets
        qs = Item.objects.defer('name', 'creator')
        q2 = pickle.loads(pickle.dumps(qs))
        self.assertEqual(list(qs), list(q2))
        q3 = pickle.loads(pickle.dumps(qs, pickle.HIGHEST_PROTOCOL))
        self.assertEqual(list(qs), list(q3))

    def test_ticket7277(self):
        self.assertQuerysetEqual(
            self.n1.annotation_set.filter(Q(tag=self.t5) | Q(tag__children=self.t5) | Q(tag__children__children=self.t5)),
            ['<Annotation: a1>']
        )

    def test_tickets_7448_7707(self):
        # Complex objects should be converted to strings before being used in
        # lookups.
        self.assertQuerysetEqual(
            Item.objects.filter(created__in=[self.time1, self.time2]),
            ['<Item: one>', '<Item: two>']
        )

    def test_ticket7235(self):
        # An EmptyQuerySet should not raise exceptions if it is filtered.
        q = EmptyQuerySet()
        self.assertQuerysetEqual(q.all(), [])
        self.assertQuerysetEqual(q.filter(x=10), [])
        self.assertQuerysetEqual(q.exclude(y=3), [])
        self.assertQuerysetEqual(q.complex_filter({'pk': 1}), [])
        self.assertQuerysetEqual(q.select_related('spam', 'eggs'), [])
        self.assertQuerysetEqual(q.annotate(Count('eggs')), [])
        self.assertQuerysetEqual(q.order_by('-pub_date', 'headline'), [])
        self.assertQuerysetEqual(q.distinct(), [])
        self.assertQuerysetEqual(
            q.extra(select={'is_recent': "pub_date > '2006-01-01'"}),
            []
        )
        q.query.low_mark = 1
        self.assertRaisesMessage(
            AssertionError,
            'Cannot change a query once a slice has been taken',
            q.extra, select={'is_recent': "pub_date > '2006-01-01'"}
        )
        self.assertQuerysetEqual(q.reverse(), [])
        self.assertQuerysetEqual(q.defer('spam', 'eggs'), [])
        self.assertQuerysetEqual(q.only('spam', 'eggs'), [])

    def test_ticket7791(self):
        # There were "issues" when ordering and distinct-ing on fields related
        # via ForeignKeys.
        self.assertEqual(
            len(Note.objects.order_by('extrainfo__info').distinct()),
            3
        )

        # Pickling of DateQuerySets used to fail
        qs = Item.objects.dates('created', 'month')
        _ = pickle.loads(pickle.dumps(qs))

    def test_ticket9997(self):
        # If a ValuesList or Values queryset is passed as an inner query, we
        # make sure it's only requesting a single value and use that as the
        # thing to select.
        self.assertQuerysetEqual(
            Tag.objects.filter(name__in=Tag.objects.filter(parent=self.t1).values('name')),
            ['<Tag: t2>', '<Tag: t3>']
        )

        # Multi-valued values() and values_list() querysets should raise errors.
        self.assertRaisesMessage(
            TypeError,
            'Cannot use a multi-field ValuesQuerySet as a filter value.',
            lambda: Tag.objects.filter(name__in=Tag.objects.filter(parent=self.t1).values('name', 'id'))
        )
        self.assertRaisesMessage(
            TypeError,
            'Cannot use a multi-field ValuesListQuerySet as a filter value.',
            lambda: Tag.objects.filter(name__in=Tag.objects.filter(parent=self.t1).values_list('name', 'id'))
        )

    def test_ticket9985(self):
        # qs.values_list(...).values(...) combinations should work.
        self.assertValueQuerysetEqual(
            Note.objects.values_list("note", flat=True).values("id").order_by("id"),
            [{'id': 1}, {'id': 2}, {'id': 3}]
        )
        self.assertQuerysetEqual(
            Annotation.objects.filter(notes__in=Note.objects.filter(note="n1").values_list('note').values('id')),
            ['<Annotation: a1>']
        )

    def test_ticket10205(self):
        # When bailing out early because of an empty "__in" filter, we need
        # to set things up correctly internally so that subqueries can continue properly.
        self.assertEqual(Tag.objects.filter(name__in=()).update(name="foo"), 0)

    def test_ticket10432(self):
        # Testing an empty "__in" filter with a generator as the value.
        def f():
            return iter([])
        n_obj = Note.objects.all()[0]
        def g():
            for i in [n_obj.pk]:
                yield i
        self.assertQuerysetEqual(Note.objects.filter(pk__in=f()), [])
        self.assertEqual(list(Note.objects.filter(pk__in=g())), [n_obj])

    def test_ticket10742(self):
        # Queries used in an __in clause don't execute subqueries

        subq = Author.objects.filter(num__lt=3000)
        qs = Author.objects.filter(pk__in=subq)
        self.assertQuerysetEqual(qs, ['<Author: a1>', '<Author: a2>'])

        # The subquery result cache should not be populated
        self.assertTrue(subq._result_cache is None)

        subq = Author.objects.filter(num__lt=3000)
        qs = Author.objects.exclude(pk__in=subq)
        self.assertQuerysetEqual(qs, ['<Author: a3>', '<Author: a4>'])

        # The subquery result cache should not be populated
        self.assertTrue(subq._result_cache is None)

        subq = Author.objects.filter(num__lt=3000)
        self.assertQuerysetEqual(
            Author.objects.filter(Q(pk__in=subq) & Q(name='a1')),
            ['<Author: a1>']
        )

        # The subquery result cache should not be populated
        self.assertTrue(subq._result_cache is None)

    def test_ticket7076(self):
        # Excluding shouldn't eliminate NULL entries.
        self.assertQuerysetEqual(
            Item.objects.exclude(modified=self.time1).order_by('name'),
            ['<Item: four>', '<Item: three>', '<Item: two>']
        )
        self.assertQuerysetEqual(
            Tag.objects.exclude(parent__name=self.t1.name),
            ['<Tag: t1>', '<Tag: t4>', '<Tag: t5>']
        )

    def test_ticket7181(self):
        # Ordering by related tables should accomodate nullable fields (this
        # test is a little tricky, since NULL ordering is database dependent.
        # Instead, we just count the number of results).
        self.assertEqual(len(Tag.objects.order_by('parent__name')), 5)

        # Empty querysets can be merged with others.
        self.assertQuerysetEqual(
            Note.objects.none() | Note.objects.all(),
            ['<Note: n1>', '<Note: n2>', '<Note: n3>']
        )
        self.assertQuerysetEqual(
            Note.objects.all() | Note.objects.none(),
            ['<Note: n1>', '<Note: n2>', '<Note: n3>']
        )
        self.assertQuerysetEqual(Note.objects.none() & Note.objects.all(), [])
        self.assertQuerysetEqual(Note.objects.all() & Note.objects.none(), [])

    def test_ticket9411(self):
        # Make sure bump_prefix() (an internal Query method) doesn't (re-)break. It's
        # sufficient that this query runs without error.
        qs = Tag.objects.values_list('id', flat=True).order_by('id')
        qs.query.bump_prefix()
        first = qs[0]
        self.assertEqual(list(qs), range(first, first+5))

    def test_ticket8439(self):
        # Complex combinations of conjunctions, disjunctions and nullable
        # relations.
        self.assertQuerysetEqual(
            Author.objects.filter(Q(item__note__extrainfo=self.e2)|Q(report=self.r1, name='xyz')),
            ['<Author: a2>']
        )
        self.assertQuerysetEqual(
            Author.objects.filter(Q(report=self.r1, name='xyz')|Q(item__note__extrainfo=self.e2)),
            ['<Author: a2>']
        )
        self.assertQuerysetEqual(
            Annotation.objects.filter(Q(tag__parent=self.t1)|Q(notes__note='n1', name='a1')),
            ['<Annotation: a1>']
        )
        xx = ExtraInfo.objects.create(info='xx', note=self.n3)
        self.assertQuerysetEqual(
            Note.objects.filter(Q(extrainfo__author=self.a1)|Q(extrainfo=xx)),
            ['<Note: n1>', '<Note: n3>']
        )
        xx.delete()
        q = Note.objects.filter(Q(extrainfo__author=self.a1)|Q(extrainfo=xx)).query
        self.assertEqual(
            len([x[2] for x in q.alias_map.values() if x[2] == q.LOUTER and q.alias_refcount[x[1]]]),
            1
        )


class Queries2Tests(TestCase):
    def setUp(self):
        Number.objects.create(num=4)
        Number.objects.create(num=8)
        Number.objects.create(num=12)

    def test_ticket4289(self):
        # A slight variation on the restricting the filtering choices by the
        # lookup constraints.
        self.assertQuerysetEqual(Number.objects.filter(num__lt=4), [])
        self.assertQuerysetEqual(Number.objects.filter(num__gt=8, num__lt=12), [])
        self.assertQuerysetEqual(
            Number.objects.filter(num__gt=8, num__lt=13),
            ['<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(Q(num__lt=4) | Q(num__gt=8, num__lt=12)),
            []
        )
        self.assertQuerysetEqual(
            Number.objects.filter(Q(num__gt=8, num__lt=12) | Q(num__lt=4)),
            []
        )
        self.assertQuerysetEqual(
            Number.objects.filter(Q(num__gt=8) & Q(num__lt=12) | Q(num__lt=4)),
            []
        )
        self.assertQuerysetEqual(
            Number.objects.filter(Q(num__gt=7) & Q(num__lt=12) | Q(num__lt=4)),
            ['<Number: 8>']
        )

    def test_ticket12239(self):
        # Float was being rounded to integer on gte queries on integer field.  Tests
        # show that gt, lt, gte, and lte work as desired.  Note that the fix changes
        # get_prep_lookup for gte and lt queries only.
        self.assertQuerysetEqual(
            Number.objects.filter(num__gt=11.9),
            ['<Number: 12>']
        )
        self.assertQuerysetEqual(Number.objects.filter(num__gt=12), [])
        self.assertQuerysetEqual(Number.objects.filter(num__gt=12.0), [])
        self.assertQuerysetEqual(Number.objects.filter(num__gt=12.1), [])
        self.assertQuerysetEqual(
            Number.objects.filter(num__lt=12),
            ['<Number: 4>', '<Number: 8>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lt=12.0),
            ['<Number: 4>', '<Number: 8>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lt=12.1),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__gte=11.9),
            ['<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__gte=12),
            ['<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__gte=12.0),
            ['<Number: 12>']
        )
        self.assertQuerysetEqual(Number.objects.filter(num__gte=12.1), [])
        self.assertQuerysetEqual(Number.objects.filter(num__gte=12.9), [])
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=11.9),
            ['<Number: 4>', '<Number: 8>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.0),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.1),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>']
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.9),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>']
        )

    def test_ticket7411(self):
        # Saving to db must work even with partially read result set in another
        # cursor.
        for num in range(2 * ITER_CHUNK_SIZE + 1):
            _ = Number.objects.create(num=num)

        for i, obj in enumerate(Number.objects.all()):
            obj.save()
            if i > 10: break

    def test_ticket7759(self):
        # Count should work with a partially read result set.
        count = Number.objects.count()
        qs = Number.objects.all()
        def run():
            for obj in qs:
                return qs.count() == count
        self.assertTrue(run())


class Queries3Tests(BaseQuerysetTest):
    def test_ticket7107(self):
        # This shouldn't create an infinite loop.
        self.assertQuerysetEqual(Valid.objects.all(), [])

    def test_ticket8683(self):
        # Raise proper error when a DateQuerySet gets passed a wrong type of
        # field
        self.assertRaisesMessage(
            AssertionError,
            "'name' isn't a DateField.",
            Item.objects.dates, 'name', 'month'
        )

class Queries4Tests(BaseQuerysetTest):
    def setUp(self):
        generic = NamedCategory.objects.create(name="Generic")
        self.t1 = Tag.objects.create(name='t1', category=generic)

        n1 = Note.objects.create(note='n1', misc='foo', id=1)
        n2 = Note.objects.create(note='n2', misc='bar', id=2)

        e1 = ExtraInfo.objects.create(info='e1', note=n1)
        e2 = ExtraInfo.objects.create(info='e2', note=n2)

        a1 = Author.objects.create(name='a1', num=1001, extra=e1)
        a3 = Author.objects.create(name='a3', num=3003, extra=e2)

        Report.objects.create(name='r1', creator=a1)
        Report.objects.create(name='r2', creator=a3)
        Report.objects.create(name='r3')

    def test_ticket7095(self):
        # Updates that are filtered on the model being updated are somewhat
        # tricky in MySQL. This exercises that case.
        ManagedModel.objects.create(data='mm1', tag=self.t1, public=True)
        self.assertEqual(ManagedModel.objects.update(data='mm'), 1)

        # A values() or values_list() query across joined models must use outer
        # joins appropriately.
        # Note: In Oracle, we expect a null CharField to return u'' instead of
        # None.
        if connection.features.interprets_empty_strings_as_nulls:
            expected_null_charfield_repr = u''
        else:
            expected_null_charfield_repr = None
        self.assertValueQuerysetEqual(
            Report.objects.values_list("creator__extra__info", flat=True).order_by("name"),
            [u'e1', u'e2', expected_null_charfield_repr],
        )

        # Similarly for select_related(), joins beyond an initial nullable join
        # must use outer joins so that all results are included.
        self.assertQuerysetEqual(
            Report.objects.select_related("creator", "creator__extra").order_by("name"),
            ['<Report: r1>', '<Report: r2>', '<Report: r3>']
        )

        # When there are multiple paths to a table from another table, we have
        # to be careful not to accidentally reuse an inappropriate join when
        # using select_related(). We used to return the parent's Detail record
        # here by mistake.

        d1 = Detail.objects.create(data="d1")
        d2 = Detail.objects.create(data="d2")
        m1 = Member.objects.create(name="m1", details=d1)
        m2 = Member.objects.create(name="m2", details=d2)
        Child.objects.create(person=m2, parent=m1)
        obj = m1.children.select_related("person__details")[0]
        self.assertEqual(obj.person.details.data, u'd2')

    def test_order_by_resetting(self):
        # Calling order_by() with no parameters removes any existing ordering on the
        # model. But it should still be possible to add new ordering after that.
        qs = Author.objects.order_by().order_by('name')
        self.assertTrue('ORDER BY' in qs.query.get_compiler(qs.db).as_sql()[0])

    def test_ticket10181(self):
        # Avoid raising an EmptyResultSet if an inner query is probably
        # empty (and hence, not executed).
        self.assertQuerysetEqual(
            Tag.objects.filter(id__in=Tag.objects.filter(id__in=[])),
            []
        )


class Queries5Tests(TestCase):
    def setUp(self):
        # Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the Meta.ordering
        # will be rank3, rank2, rank1.
        n1 = Note.objects.create(note='n1', misc='foo', id=1)
        n2 = Note.objects.create(note='n2', misc='bar', id=2)
        e1 = ExtraInfo.objects.create(info='e1', note=n1)
        e2 = ExtraInfo.objects.create(info='e2', note=n2)
        a1 = Author.objects.create(name='a1', num=1001, extra=e1)
        a2 = Author.objects.create(name='a2', num=2002, extra=e1)
        a3 = Author.objects.create(name='a3', num=3003, extra=e2)
        self.rank1 = Ranking.objects.create(rank=2, author=a2)
        Ranking.objects.create(rank=1, author=a3)
        Ranking.objects.create(rank=3, author=a1)

    def test_ordering(self):
        # Cross model ordering is possible in Meta, too.
        self.assertQuerysetEqual(
            Ranking.objects.all(),
            ['<Ranking: 3: a1>', '<Ranking: 2: a2>', '<Ranking: 1: a3>']
        )
        self.assertQuerysetEqual(
            Ranking.objects.all().order_by('rank'),
            ['<Ranking: 1: a3>', '<Ranking: 2: a2>', '<Ranking: 3: a1>']
        )


        # Ordering of extra() pieces is possible, too and you can mix extra
        # fields and model fields in the ordering.
        self.assertQuerysetEqual(
            Ranking.objects.extra(tables=['django_site'], order_by=['-django_site.id', 'rank']),
            ['<Ranking: 1: a3>', '<Ranking: 2: a2>', '<Ranking: 3: a1>']
        )

        qs = Ranking.objects.extra(select={'good': 'case when rank > 2 then 1 else 0 end'})
        self.assertEqual(
            [o.good for o in qs.extra(order_by=('-good',))],
            [True, False, False]
        )
        self.assertQuerysetEqual(
            qs.extra(order_by=('-good', 'id')),
            ['<Ranking: 3: a1>', '<Ranking: 2: a2>', '<Ranking: 1: a3>']
        )

        # Despite having some extra aliases in the query, we can still omit
        # them in a values() query.
        dicts = qs.values('id', 'rank').order_by('id')
        self.assertEqual(
            [d.items()[1] for d in dicts],
            [('rank', 2), ('rank', 1), ('rank', 3)]
        )

    def test_ticket7256(self):
        # An empty values() call includes all aliases, including those from an
        # extra()
        qs = Ranking.objects.extra(select={'good': 'case when rank > 2 then 1 else 0 end'})
        dicts = qs.values().order_by('id')
        for d in dicts: del d['id']; del d['author_id']
        self.assertEqual(
            [sorted(d.items()) for d in dicts],
            [[('good', 0), ('rank', 2)], [('good', 0), ('rank', 1)], [('good', 1), ('rank', 3)]]
        )

    def test_ticket7045(self):
        # Extra tables used to crash SQL construction on the second use.
        qs = Ranking.objects.extra(tables=['django_site'])
        qs.query.get_compiler(qs.db).as_sql()
        # test passes if this doesn't raise an exception.
        qs.query.get_compiler(qs.db).as_sql()

    def test_ticket9848(self):
        # Make sure that updates which only filter on sub-tables don't
        # inadvertently update the wrong records (bug #9848).

        # Make sure that the IDs from different tables don't happen to match.
        self.assertQuerysetEqual(
            Ranking.objects.filter(author__name='a1'),
            ['<Ranking: 3: a1>']
        )
        self.assertEqual(
            Ranking.objects.filter(author__name='a1').update(rank='4'),
            1
        )
        r = Ranking.objects.filter(author__name='a1')[0]
        self.assertNotEqual(r.id, r.author.id)
        self.assertEqual(r.rank, 4)
        r.rank = 3
        r.save()
        self.assertQuerysetEqual(
            Ranking.objects.all(),
            ['<Ranking: 3: a1>', '<Ranking: 2: a2>', '<Ranking: 1: a3>']
        )

    def test_ticket5261(self):
        self.assertQuerysetEqual(
            Note.objects.exclude(Q()),
            ['<Note: n1>', '<Note: n2>']
        )


class SelectRelatedTests(TestCase):
    def test_tickets_3045_3288(self):
        # Once upon a time, select_related() with circular relations would loop
        # infinitely if you forgot to specify "depth". Now we set an arbitrary
        # default upper bound.
        self.assertQuerysetEqual(X.objects.all(), [])
        self.assertQuerysetEqual(X.objects.select_related(), [])


class SubclassFKTests(TestCase):
    def test_ticket7778(self):
        # Model subclasses could not be deleted if a nullable foreign key
        # relates to a model that relates back.

        num_celebs = Celebrity.objects.count()
        tvc = TvChef.objects.create(name="Huey")
        self.assertEqual(Celebrity.objects.count(), num_celebs + 1)
        Fan.objects.create(fan_of=tvc)
        Fan.objects.create(fan_of=tvc)
        tvc.delete()

        # The parent object should have been deleted as well.
        self.assertEqual(Celebrity.objects.count(), num_celebs)


class CustomPkTests(TestCase):
    def test_ticket7371(self):
        self.assertQuerysetEqual(Related.objects.order_by('custom'), [])


class NullableRelOrderingTests(TestCase):
    def test_ticket10028(self):
        # Ordering by model related to nullable relations(!) should use outer
        # joins, so that all results are included.
        _ = Plaything.objects.create(name="p1")
        self.assertQuerysetEqual(
            Plaything.objects.all(),
            ['<Plaything: p1>']
        )


class DisjunctiveFilterTests(TestCase):
    def setUp(self):
        self.n1 = Note.objects.create(note='n1', misc='foo', id=1)
        ExtraInfo.objects.create(info='e1', note=self.n1)

    def test_ticket7872(self):
        # Another variation on the disjunctive filtering theme.

        # For the purposes of this regression test, it's important that there is no
        # Join object releated to the LeafA we create.
        LeafA.objects.create(data='first')
        self.assertQuerysetEqual(LeafA.objects.all(), ['<LeafA: first>'])
        self.assertQuerysetEqual(
            LeafA.objects.filter(Q(data='first')|Q(join__b__data='second')),
            ['<LeafA: first>']
        )

    def test_ticket8283(self):
        # Checking that applying filters after a disjunction works correctly.
        self.assertQuerysetEqual(
            (ExtraInfo.objects.filter(note=self.n1)|ExtraInfo.objects.filter(info='e2')).filter(note=self.n1),
            ['<ExtraInfo: e1>']
        )
        self.assertQuerysetEqual(
            (ExtraInfo.objects.filter(info='e2')|ExtraInfo.objects.filter(note=self.n1)).filter(note=self.n1),
            ['<ExtraInfo: e1>']
        )


class Queries6Tests(TestCase):
    def setUp(self):
        generic = NamedCategory.objects.create(name="Generic")
        t1 = Tag.objects.create(name='t1', category=generic)
        t2 = Tag.objects.create(name='t2', parent=t1, category=generic)
        t3 = Tag.objects.create(name='t3', parent=t1)
        t4 = Tag.objects.create(name='t4', parent=t3)
        t5 = Tag.objects.create(name='t5', parent=t3)
        n1 = Note.objects.create(note='n1', misc='foo', id=1)
        ann1 = Annotation.objects.create(name='a1', tag=t1)
        ann1.notes.add(n1)
        ann2 = Annotation.objects.create(name='a2', tag=t4)

    # FIXME!! This next test causes really weird PostgreSQL behaviour, but it's
    # only apparent much later when the full test suite runs. I don't understand
    # what's going on here yet.
    ##def test_slicing_and_cache_interaction(self):
    ##    # We can do slicing beyond what is currently in the result cache,
    ##    # too.
    ##
    ##    # We need to mess with the implementation internals a bit here to decrease the
    ##    # cache fill size so that we don't read all the results at once.
    ##    from django.db.models import query
    ##    query.ITER_CHUNK_SIZE = 2
    ##    qs = Tag.objects.all()
    ##
    ##    # Fill the cache with the first chunk.
    ##    self.assertTrue(bool(qs))
    ##    self.assertEqual(len(qs._result_cache), 2)
    ##
    ##    # Query beyond the end of the cache and check that it is filled out as required.
    ##    self.assertEqual(repr(qs[4]), '<Tag: t5>')
    ##    self.assertEqual(len(qs._result_cache), 5)
    ##
    ##    # But querying beyond the end of the result set will fail.
    ##    self.assertRaises(IndexError, lambda: qs[100])

    def test_parallel_iterators(self):
        # Test that parallel iterators work.
        qs = Tag.objects.all()
        i1, i2 = iter(qs), iter(qs)
        self.assertEqual(repr(i1.next()), '<Tag: t1>')
        self.assertEqual(repr(i1.next()), '<Tag: t2>')
        self.assertEqual(repr(i2.next()), '<Tag: t1>')
        self.assertEqual(repr(i2.next()), '<Tag: t2>')
        self.assertEqual(repr(i2.next()), '<Tag: t3>')
        self.assertEqual(repr(i1.next()), '<Tag: t3>')

        qs = X.objects.all()
        self.assertEqual(bool(qs), False)
        self.assertEqual(bool(qs), False)

    def test_nested_queries_sql(self):
        # Nested queries should not evaluate the inner query as part of constructing the
        # SQL (so we should see a nested query here, indicated by two "SELECT" calls).
        qs = Annotation.objects.filter(notes__in=Note.objects.filter(note="xyzzy"))
        self.assertEqual(
            qs.query.get_compiler(qs.db).as_sql()[0].count('SELECT'),
            2
        )

    def test_tickets_8921_9188(self):
        # Incorrect SQL was being generated for certain types of exclude()
        # queries that crossed multi-valued relations (#8921, #9188 and some
        # pre-emptively discovered cases).

        self.assertQuerysetEqual(
            PointerA.objects.filter(connection__pointerb__id=1),
            []
        )
        self.assertQuerysetEqual(
            PointerA.objects.exclude(connection__pointerb__id=1),
            []
        )

        # This next makes exactly *zero* sense, but it works. It's needed
        # because MySQL fails to give the right results the first time this
        # query is executed. If you run the same query a second time, it
        # works fine. It's a hack, but it works...
        list(Tag.objects.exclude(children=None))
        self.assertQuerysetEqual(
            Tag.objects.exclude(children=None),
            ['<Tag: t1>', '<Tag: t3>']
        )

        # This example is tricky because the parent could be NULL, so only checking
        # parents with annotations omits some results (tag t1, in this case).
        self.assertQuerysetEqual(
            Tag.objects.exclude(parent__annotation__name="a1"),
            ['<Tag: t1>', '<Tag: t4>', '<Tag: t5>']
        )

        # The annotation->tag link is single values and tag->children links is
        # multi-valued. So we have to split the exclude filter in the middle
        # and then optimise the inner query without losing results.
        self.assertQuerysetEqual(
            Annotation.objects.exclude(tag__children__name="t2"),
            ['<Annotation: a2>']
        )

        # Nested queries are possible (although should be used with care, since
        # they have performance problems on backends like MySQL.

        self.assertQuerysetEqual(
            Annotation.objects.filter(notes__in=Note.objects.filter(note="n1")),
            ['<Annotation: a1>']
        )

    def test_ticket3739(self):
        # The all() method on querysets returns a copy of the queryset.
        q1 = Tag.objects.order_by('name')
        self.assertTrue(q1 is not q1.all())


class GeneratorExpressionTests(TestCase):
    def test_ticket10432(self):
        # Using an empty generator expression as the rvalue for an "__in"
        # lookup is legal.
        self.assertQuerysetEqual(
            Note.objects.filter(pk__in=(x for x in ())),
            []
        )


class ComparisonTests(TestCase):
    def setUp(self):
        self.n1 = Note.objects.create(note='n1', misc='foo', id=1)
        e1 = ExtraInfo.objects.create(info='e1', note=self.n1)
        self.a2 = Author.objects.create(name='a2', num=2002, extra=e1)

    def test_ticket8597(self):
        # Regression tests for case-insensitive comparisons
        _ = Item.objects.create(name="a_b", created=datetime.datetime.now(), creator=self.a2, note=self.n1)
        _ = Item.objects.create(name="x%y", created=datetime.datetime.now(), creator=self.a2, note=self.n1)
        self.assertQuerysetEqual(
            Item.objects.filter(name__iexact="A_b"),
            ['<Item: a_b>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(name__iexact="x%Y"),
            ['<Item: x%y>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(name__istartswith="A_b"),
            ['<Item: a_b>']
        )
        self.assertQuerysetEqual(
            Item.objects.filter(name__iendswith="A_b"),
            ['<Item: a_b>']
        )


class ExistsSql(TestCase):
    def setUp(self):
        settings.DEBUG = True

    def test_exists(self):
        self.assertFalse(Tag.objects.exists())
        # Ok - so the exist query worked - but did it include too many columns?
        self.assertTrue("id" not in connection.queries[-1]['sql'] and "name" not in connection.queries[-1]['sql'])

    def tearDown(self):
        settings.DEBUG = False


class QuerysetOrderedTests(unittest.TestCase):
    """
    Tests for the Queryset.ordered attribute.
    """

    def test_no_default_or_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().ordered, False)

    def test_cleared_default_ordering(self):
        self.assertEqual(Tag.objects.all().ordered, True)
        self.assertEqual(Tag.objects.all().order_by().ordered, False)

    def test_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().order_by('id').ordered, True)

    def test_order_by_extra(self):
        self.assertEqual(Annotation.objects.all().extra(order_by=['id']).ordered, True)

    def test_annotated_ordering(self):
        qs = Annotation.objects.annotate(num_notes=Count('notes'))
        self.assertEqual(qs.ordered, False)
        self.assertEqual(qs.order_by('num_notes').ordered, True)


class SubqueryTests(TestCase):
    def setUp(self):
        DumbCategory.objects.create(id=1)
        DumbCategory.objects.create(id=2)
        DumbCategory.objects.create(id=3)

    def test_ordered_subselect(self):
        "Subselects honor any manual ordering"
        try:
            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[2:])
            self.assertEquals(set(query.values_list('id', flat=True)), set([1]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connections[DEFAULT_DB_ALIAS].features.allow_sliced_subqueries)

    def test_sliced_delete(self):
        "Delete queries can safely contain sliced subqueries"
        try:
            DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:1]).delete()
            self.assertEquals(set(DumbCategory.objects.values_list('id', flat=True)), set([1,2]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connections[DEFAULT_DB_ALIAS].features.allow_sliced_subqueries)


class CloneTests(TestCase):
    def test_evaluated_queryset_as_argument(self):
        "#13227 -- If a queryset is already evaluated, it can still be used as a query arg"
        n = Note(note='Test1', misc='misc')
        n.save()
        e = ExtraInfo(info='good', note=n)
        e.save()

        n_list = Note.objects.all()
        # Evaluate the Note queryset, populating the query cache
        list(n_list)
        # Use the note queryset in a query, and evalute
        # that query in a way that involves cloning.
        try:
            self.assertEquals(ExtraInfo.objects.filter(note__in=n_list)[0].info, 'good')
        except:
            self.fail('Query should be clonable')


class EmptyQuerySetTests(TestCase):
    def test_emptyqueryset_values(self):
        # #14366 -- Calling .values() on an EmptyQuerySet and then cloning that
        # should not cause an error"
        self.assertQuerysetEqual(
            Number.objects.none().values('num').order_by('num'), []
        )

    def test_values_subquery(self):
        self.assertQuerysetEqual(
            Number.objects.filter(pk__in=Number.objects.none().values("pk")),
            []
        )
        self.assertQuerysetEqual(
            Number.objects.filter(pk__in=Number.objects.none().values_list("pk")),
            []
        )


class ValuesQuerysetTests(BaseQuerysetTest):
    def test_flat_values_lits(self):
        Number.objects.create(num=72)
        qs = Number.objects.values_list("num")
        qs = qs.values_list("num", flat=True)
        self.assertValueQuerysetEqual(
            qs, [72]
        )


class WeirdQuerysetSlicingTests(BaseQuerysetTest):
    def setUp(self):
        Number.objects.create(num=1)
        Number.objects.create(num=2)

        Article.objects.create(name='one', created=datetime.datetime.now())
        Article.objects.create(name='two', created=datetime.datetime.now())
        Article.objects.create(name='three', created=datetime.datetime.now())
        Article.objects.create(name='four', created=datetime.datetime.now())

    def test_tickets_7698_10202(self):
        # People like to slice with '0' as the high-water mark.
        self.assertQuerysetEqual(Article.objects.all()[0:0], [])
        self.assertQuerysetEqual(Article.objects.all()[0:0][:10], [])
        self.assertEqual(Article.objects.all()[:0].count(), 0)
        self.assertRaisesMessage(
            AssertionError,
            'Cannot change a query once a slice has been taken.',
            Article.objects.all()[:0].latest, 'created'
        )


class EscapingTests(TestCase):
    def test_ticket_7302(self):
        # Reserved names are appropriately escaped
        _ = ReservedName.objects.create(name='a', order=42)
        ReservedName.objects.create(name='b', order=37)
        self.assertQuerysetEqual(
            ReservedName.objects.all().order_by('order'),
            ['<ReservedName: b>', '<ReservedName: a>']
        )
        self.assertQuerysetEqual(
            ReservedName.objects.extra(select={'stuff':'name'}, order_by=('order','stuff')),
            ['<ReservedName: b>', '<ReservedName: a>']
        )


class ToFieldTests(TestCase):
    def test_in_query(self):
        apple = Food.objects.create(name="apple")
        pear = Food.objects.create(name="pear")
        lunch = Eaten.objects.create(food=apple, meal="lunch")
        dinner = Eaten.objects.create(food=pear, meal="dinner")

        self.assertEqual(
            set(Eaten.objects.filter(food__in=[apple, pear])),
            set([lunch, dinner]),
        )

    def test_reverse_in(self):
        apple = Food.objects.create(name="apple")
        pear = Food.objects.create(name="pear")
        lunch_apple = Eaten.objects.create(food=apple, meal="lunch")
        lunch_pear = Eaten.objects.create(food=pear, meal="dinner")

        self.assertEqual(
            set(Food.objects.filter(eaten__in=[lunch_apple, lunch_pear])),
            set([apple, pear])
        )

    def test_single_object(self):
        apple = Food.objects.create(name="apple")
        lunch = Eaten.objects.create(food=apple, meal="lunch")
        dinner = Eaten.objects.create(food=apple, meal="dinner")

        self.assertEqual(
            set(Eaten.objects.filter(food=apple)),
            set([lunch, dinner])
        )

    def test_single_object_reverse(self):
        apple = Food.objects.create(name="apple")
        lunch = Eaten.objects.create(food=apple, meal="lunch")

        self.assertEqual(
            set(Food.objects.filter(eaten=lunch)),
            set([apple])
        )

    def test_recursive_fk(self):
        node1 = Node.objects.create(num=42)
        node2 = Node.objects.create(num=1, parent=node1)

        self.assertEqual(
            list(Node.objects.filter(parent=node1)),
            [node2]
        )

    def test_recursive_fk_reverse(self):
        node1 = Node.objects.create(num=42)
        node2 = Node.objects.create(num=1, parent=node1)

        self.assertEqual(
            list(Node.objects.filter(node=node2)),
            [node1]
        )


# In Python 2.6 beta releases, exceptions raised in __len__ are swallowed
# (Python issue 1242657), so these cases return an empty list, rather than
# raising an exception. Not a lot we can do about that, unfortunately, due to
# the way Python handles list() calls internally. Thus, we skip the tests for
# Python 2.6.
if sys.version_info[:2] != (2, 6):
    class OrderingLoopTests(BaseQuerysetTest):
        def setUp(self):
            generic = NamedCategory.objects.create(name="Generic")
            t1 = Tag.objects.create(name='t1', category=generic)
            t2 = Tag.objects.create(name='t2', parent=t1, category=generic)
            t3 = Tag.objects.create(name='t3', parent=t1)
            t4 = Tag.objects.create(name='t4', parent=t3)
            t5 = Tag.objects.create(name='t5', parent=t3)

        def test_infinite_loop(self):
            # If you're not careful, it's possible to introduce infinite loops via
            # default ordering on foreign keys in a cycle. We detect that.
            self.assertRaisesMessage(
                FieldError,
                'Infinite loop caused by ordering.',
                lambda: list(LoopX.objects.all()) # Force queryset evaluation with list()
            )
            self.assertRaisesMessage(
                FieldError,
                'Infinite loop caused by ordering.',
                lambda: list(LoopZ.objects.all()) # Force queryset evaluation with list()
            )

            # Note that this doesn't cause an infinite loop, since the default
            # ordering on the Tag model is empty (and thus defaults to using "id"
            # for the related field).
            self.assertEqual(len(Tag.objects.order_by('parent')), 5)

            # ... but you can still order in a non-recursive fashion amongst linked
            # fields (the previous test failed because the default ordering was
            # recursive).
            self.assertQuerysetEqual(
                LoopX.objects.all().order_by('y__x__y__x__id'),
                []
            )


# When grouping without specifying ordering, we add an explicit "ORDER BY NULL"
# portion in MySQL to prevent unnecessary sorting.
if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == "django.db.backends.mysql":
    class GroupingTests(TestCase):
        def test_null_ordering_added(self):
            query = Tag.objects.values_list('parent_id', flat=True).order_by().query
            query.group_by = ['parent_id']
            sql = query.get_compiler(DEFAULT_DB_ALIAS).as_sql()[0]
            fragment = "ORDER BY "
            pos = sql.find(fragment)
            self.assertEqual(sql.find(fragment, pos + 1), -1)
            self.assertEqual(sql.find("NULL", pos + len(fragment)), pos + len(fragment))


# Sqlite 3 does not support passing in more than 1000 parameters except by
# changing a parameter at compilation time.
if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != "django.db.backends.sqlite3":
    class InLookupTests(TestCase):
        def test_ticket14244(self):
            # Test that the "in" lookup works with lists of 1000 items or more.
            Number.objects.all().delete()
            numbers = range(2500)
            for num in numbers:
                _ = Number.objects.create(num=num)
            self.assertEqual(
                Number.objects.filter(num__in=numbers[:1000]).count(),
                1000
            )
            self.assertEqual(
                Number.objects.filter(num__in=numbers[:1001]).count(),
                1001
            )
            self.assertEqual(
                Number.objects.filter(num__in=numbers[:2000]).count(),
                2000
            )
            self.assertEqual(
                Number.objects.filter(num__in=numbers).count(),
                2500
            )
