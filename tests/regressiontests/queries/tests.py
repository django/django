from __future__ import absolute_import,unicode_literals

import datetime
from operator import attrgetter
import pickle
import sys

from django.conf import settings
from django.core.exceptions import FieldError
from django.db import DatabaseError, connection, connections, DEFAULT_DB_ALIAS
from django.db.models import Count, F, Q
from django.db.models.query import ITER_CHUNK_SIZE
from django.db.models.sql.where import WhereNode, EverythingNode, NothingNode
from django.db.models.sql.datastructures import EmptyResultSet
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import str_prefix
from django.utils import unittest
from django.utils.datastructures import SortedDict

from .models import (Annotation, Article, Author, Celebrity, Child, Cover,
    Detail, DumbCategory, ExtraInfo, Fan, Item, LeafA, LoopX, LoopZ,
    ManagedModel, Member, NamedCategory, Note, Number, Plaything, PointerA,
    Ranking, Related, Report, ReservedName, Tag, TvChef, Valid, X, Food, Eaten,
    Node, ObjectA, ObjectB, ObjectC, CategoryItem, SimpleCategory,
    SpecialCategory, OneToOneCategory, NullableName, ProxyCategory,
    SingleObject, RelatedObject, ModelA, ModelD, Responsibility, Job,
    JobResponsibilities, BaseA)


class BaseQuerysetTest(TestCase):
    def assertValueQuerysetEqual(self, qs, values):
        return self.assertQuerysetEqual(qs, values, transform=lambda x: x)


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

        q1 = Item.objects.filter(tags=self.t1)
        q2 = Item.objects.filter(note=self.n3, tags=self.t2)
        q3 = Item.objects.filter(creator=self.a4)
        self.assertQuerysetEqual(
            ((q1 & q2) | q3).order_by('name'),
            ['<Item: four>', '<Item: one>']
        )

    def test_order_by_tables(self):
        q1 = Item.objects.order_by('name')
        q2 = Item.objects.filter(id=self.i1.id)
        list(q2)
        combined_query = (q1 & q2).order_by('name').query
        self.assertEqual(len([
            t for t in combined_query.tables if combined_query.alias_refcount[t]
        ]), 1)

    def test_order_by_join_unref(self):
        """
        This test is related to the above one, testing that there aren't
        old JOINs in the query.
        """
        qs = Celebrity.objects.order_by('greatest_fan__fan_of')
        self.assertIn('OUTER JOIN', str(qs.query))
        qs = qs.order_by('id')
        self.assertNotIn('OUTER JOIN', str(qs.query))

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
            [{'misc': 'foo'}, {'misc': 'bar'}, {'misc': 'foo'}]
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
        self.assertEqual(d, {'a': 'one', 'b': 'two'})

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
            [{'note__note': 'n2'}, {'note__note': 'n3'}, {'note__note': 'n3'}, {'note__note': 'n3'}]
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
        Eaten.objects.create(meal='m')
        q = Eaten.objects.none()
        with self.assertNumQueries(0):
            self.assertQuerysetEqual(q.all(), [])
            self.assertQuerysetEqual(q.filter(meal='m'), [])
            self.assertQuerysetEqual(q.exclude(meal='m'), [])
            self.assertQuerysetEqual(q.complex_filter({'pk': 1}), [])
            self.assertQuerysetEqual(q.select_related('food'), [])
            self.assertQuerysetEqual(q.annotate(Count('food')), [])
            self.assertQuerysetEqual(q.order_by('meal', 'food'), [])
            self.assertQuerysetEqual(q.distinct(), [])
            self.assertQuerysetEqual(
                q.extra(select={'foo': "1"}),
                []
            )
            q.query.low_mark = 1
            self.assertRaisesMessage(
                AssertionError,
                'Cannot change a query once a slice has been taken',
                q.extra, select={'foo': "1"}
            )
            self.assertQuerysetEqual(q.reverse(), [])
            self.assertQuerysetEqual(q.defer('meal'), [])
            self.assertQuerysetEqual(q.only('meal'), [])

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
        self.assertEqual(list(qs), list(range(first, first+5)))

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

    def test_ticket17429(self):
        """
        Ensure that Meta.ordering=None works the same as Meta.ordering=[]
        """
        original_ordering = Tag._meta.ordering
        Tag._meta.ordering = None
        try:
            self.assertQuerysetEqual(
                Tag.objects.all(),
                ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>'],
                ordered=False
            )
        finally:
            Tag._meta.ordering = original_ordering

    def test_exclude(self):
        self.assertQuerysetEqual(
            Item.objects.exclude(tags__name='t4'),
            [repr(i) for i in Item.objects.filter(~Q(tags__name='t4'))])
        self.assertQuerysetEqual(
            Item.objects.exclude(Q(tags__name='t4')|Q(tags__name='t3')),
            [repr(i) for i in Item.objects.filter(~(Q(tags__name='t4')|Q(tags__name='t3')))])
        self.assertQuerysetEqual(
            Item.objects.exclude(Q(tags__name='t4')|~Q(tags__name='t3')),
            [repr(i) for i in Item.objects.filter(~(Q(tags__name='t4')|~Q(tags__name='t3')))])

    def test_nested_exclude(self):
        self.assertQuerysetEqual(
            Item.objects.exclude(~Q(tags__name='t4')),
            [repr(i) for i in Item.objects.filter(~~Q(tags__name='t4'))])

    def test_double_exclude(self):
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags__name='t4')),
            [repr(i) for i in Item.objects.filter(~~Q(tags__name='t4'))])
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags__name='t4')),
            [repr(i) for i in Item.objects.filter(~Q(~Q(tags__name='t4')))])

    @unittest.expectedFailure
    def test_exclude_in(self):
        self.assertQuerysetEqual(
            Item.objects.exclude(Q(tags__name__in=['t4', 't3'])),
            [repr(i) for i in Item.objects.filter(~Q(tags__name__in=['t4', 't3']))])
        self.assertQuerysetEqual(
            Item.objects.filter(Q(tags__name__in=['t4', 't3'])),
            [repr(i) for i in Item.objects.filter(~~Q(tags__name__in=['t4', 't3']))])

    def test_ticket_10790_1(self):
        # Querying direct fields with isnull should trim the left outer join.
        # It also should not create INNER JOIN.
        q = Tag.objects.filter(parent__isnull=True)

        self.assertQuerysetEqual(q, ['<Tag: t1>'])
        self.assertTrue('JOIN' not in str(q.query))

        q = Tag.objects.filter(parent__isnull=False)

        self.assertQuerysetEqual(
            q,
            ['<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>'],
        )
        self.assertTrue('JOIN' not in str(q.query))

        q = Tag.objects.exclude(parent__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>'],
        )
        self.assertTrue('JOIN' not in str(q.query))

        q = Tag.objects.exclude(parent__isnull=False)
        self.assertQuerysetEqual(q, ['<Tag: t1>'])
        self.assertTrue('JOIN' not in str(q.query))

        q = Tag.objects.exclude(parent__parent__isnull=False)

        self.assertQuerysetEqual(
            q,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>'],
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 1)
        self.assertTrue('INNER JOIN' not in str(q.query))

    def test_ticket_10790_2(self):
        # Querying across several tables should strip only the last outer join,
        # while preserving the preceeding inner joins.
        q = Tag.objects.filter(parent__parent__isnull=False)

        self.assertQuerysetEqual(
            q,
            ['<Tag: t4>', '<Tag: t5>'],
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 1)

        # Querying without isnull should not convert anything to left outer join.
        q = Tag.objects.filter(parent__parent=self.t1)
        self.assertQuerysetEqual(
            q,
            ['<Tag: t4>', '<Tag: t5>'],
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 1)

    def test_ticket_10790_3(self):
        # Querying via indirect fields should populate the left outer join
        q = NamedCategory.objects.filter(tag__isnull=True)
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 1)
        # join to dumbcategory ptr_id
        self.assertTrue(str(q.query).count('INNER JOIN') == 1)
        self.assertQuerysetEqual(q, [])

        # Querying across several tables should strip only the last join, while
        # preserving the preceding left outer joins.
        q = NamedCategory.objects.filter(tag__parent__isnull=True)
        self.assertTrue(str(q.query).count('INNER JOIN') == 1)
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 1)
        self.assertQuerysetEqual( q, ['<NamedCategory: NamedCategory object>'])

    def test_ticket_10790_4(self):
        # Querying across m2m field should not strip the m2m table from join.
        q = Author.objects.filter(item__tags__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Author: a2>', '<Author: a3>'],
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 2)
        self.assertTrue('INNER JOIN' not in str(q.query))

        q = Author.objects.filter(item__tags__parent__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a2>', '<Author: a2>', '<Author: a3>'],
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 3)
        self.assertTrue('INNER JOIN' not in str(q.query))

    def test_ticket_10790_5(self):
        # Querying with isnull=False across m2m field should not create outer joins
        q = Author.objects.filter(item__tags__isnull=False)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a1>', '<Author: a2>', '<Author: a2>', '<Author: a4>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 2)

        q = Author.objects.filter(item__tags__parent__isnull=False)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a2>', '<Author: a4>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 3)

        q = Author.objects.filter(item__tags__parent__parent__isnull=False)
        self.assertQuerysetEqual(
            q,
            ['<Author: a4>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 4)

    def test_ticket_10790_6(self):
        # Querying with isnull=True across m2m field should not create inner joins
        # and strip last outer join
        q = Author.objects.filter(item__tags__parent__parent__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a1>', '<Author: a2>', '<Author: a2>',
             '<Author: a2>', '<Author: a3>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 4)
        self.assertTrue(str(q.query).count('INNER JOIN') == 0)

        q = Author.objects.filter(item__tags__parent__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a2>', '<Author: a2>', '<Author: a3>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 3)
        self.assertTrue(str(q.query).count('INNER JOIN') == 0)

    def test_ticket_10790_7(self):
        # Reverse querying with isnull should not strip the join
        q = Author.objects.filter(item__isnull=True)
        self.assertQuerysetEqual(
            q,
            ['<Author: a3>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 1)
        self.assertTrue(str(q.query).count('INNER JOIN') == 0)

        q = Author.objects.filter(item__isnull=False)
        self.assertQuerysetEqual(
            q,
            ['<Author: a1>', '<Author: a2>', '<Author: a2>', '<Author: a4>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 1)

    def test_ticket_10790_8(self):
        # Querying with combined q-objects should also strip the left outer join
        q = Tag.objects.filter(Q(parent__isnull=True) | Q(parent=self.t1))
        self.assertQuerysetEqual(
            q,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>']
        )
        self.assertTrue(str(q.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q.query).count('INNER JOIN') == 0)

    def test_ticket_10790_combine(self):
        # Combining queries should not re-populate the left outer join
        q1 = Tag.objects.filter(parent__isnull=True)
        q2 = Tag.objects.filter(parent__isnull=False)

        q3 = q1 | q2
        self.assertQuerysetEqual(
            q3,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>', '<Tag: t4>', '<Tag: t5>'],
        )
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)

        q3 = q1 & q2
        self.assertQuerysetEqual(q3, [])
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)

        q2 = Tag.objects.filter(parent=self.t1)
        q3 = q1 | q2
        self.assertQuerysetEqual(
            q3,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>']
        )
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)

        q3 = q2 | q1
        self.assertQuerysetEqual(
            q3,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>']
        )
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 0)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)

        q1 = Tag.objects.filter(parent__isnull=True)
        q2 = Tag.objects.filter(parent__parent__isnull=True)

        q3 = q1 | q2
        self.assertQuerysetEqual(
            q3,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>']
        )
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 1)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)

        q3 = q2 | q1
        self.assertQuerysetEqual(
            q3,
            ['<Tag: t1>', '<Tag: t2>', '<Tag: t3>']
        )
        self.assertTrue(str(q3.query).count('LEFT OUTER JOIN') == 1)
        self.assertTrue(str(q3.query).count('INNER JOIN') == 0)


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
            ['<Number: 4>', '<Number: 8>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lt=12.0),
            ['<Number: 4>', '<Number: 8>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lt=12.1),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>'],
            ordered=False
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
            ['<Number: 4>', '<Number: 8>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.0),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.1),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Number.objects.filter(num__lte=12.9),
            ['<Number: 4>', '<Number: 8>', '<Number: 12>'],
            ordered=False
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

        self.a1 = Author.objects.create(name='a1', num=1001, extra=e1)
        self.a3 = Author.objects.create(name='a3', num=3003, extra=e2)

        self.r1 = Report.objects.create(name='r1', creator=self.a1)
        self.r2 = Report.objects.create(name='r2', creator=self.a3)
        self.r3 = Report.objects.create(name='r3')

        Item.objects.create(name='i1', created=datetime.datetime.now(), note=n1, creator=self.a1)
        Item.objects.create(name='i2', created=datetime.datetime.now(), note=n1, creator=self.a3)

    def test_ticket14876(self):
        # Note: when combining the query we need to have information available
        # about the join type of the trimmed "creator__isnull" join. If we
        # don't have that information, then the join is created as INNER JOIN
        # and results will be incorrect.
        q1 = Report.objects.filter(Q(creator__isnull=True) | Q(creator__extra__info='e1'))
        q2 = Report.objects.filter(Q(creator__isnull=True)) | Report.objects.filter(Q(creator__extra__info='e1'))
        self.assertQuerysetEqual(q1, ["<Report: r1>", "<Report: r3>"], ordered=False)
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Report.objects.filter(Q(creator__extra__info='e1') | Q(creator__isnull=True))
        q2 = Report.objects.filter(Q(creator__extra__info='e1')) | Report.objects.filter(Q(creator__isnull=True))
        self.assertQuerysetEqual(q1, ["<Report: r1>", "<Report: r3>"], ordered=False)
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Item.objects.filter(Q(creator=self.a1) | Q(creator__report__name='r1')).order_by()
        q2 = Item.objects.filter(Q(creator=self.a1)).order_by() | Item.objects.filter(Q(creator__report__name='r1')).order_by()
        self.assertQuerysetEqual(q1, ["<Item: i1>"])
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Item.objects.filter(Q(creator__report__name='e1') | Q(creator=self.a1)).order_by()
        q2 = Item.objects.filter(Q(creator__report__name='e1')).order_by() | Item.objects.filter(Q(creator=self.a1)).order_by()
        self.assertQuerysetEqual(q1, ["<Item: i1>"])
        self.assertEqual(str(q1.query), str(q2.query))

    def test_combine_join_reuse(self):
        # Test that we correctly recreate joins having identical connections
        # in the rhs query, in case the query is ORed together. Related to
        # ticket #18748
        Report.objects.create(name='r4', creator=self.a1)
        q1 = Author.objects.filter(report__name='r5')
        q2 = Author.objects.filter(report__name='r4').filter(report__name='r1')
        combined = q1|q2
        self.assertEqual(str(combined.query).count('JOIN'), 2)
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0].name, 'a1')

    def test_ticket7095(self):
        # Updates that are filtered on the model being updated are somewhat
        # tricky in MySQL. This exercises that case.
        ManagedModel.objects.create(data='mm1', tag=self.t1, public=True)
        self.assertEqual(ManagedModel.objects.update(data='mm'), 1)

        # A values() or values_list() query across joined models must use outer
        # joins appropriately.
        # Note: In Oracle, we expect a null CharField to return '' instead of
        # None.
        if connection.features.interprets_empty_strings_as_nulls:
            expected_null_charfield_repr = ''
        else:
            expected_null_charfield_repr = None
        self.assertValueQuerysetEqual(
            Report.objects.values_list("creator__extra__info", flat=True).order_by("name"),
            ['e1', 'e2', expected_null_charfield_repr],
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
        self.assertEqual(obj.person.details.data, 'd2')

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

    def test_ticket15316_filter_false(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(name="named category1",
                special_name="special1")
        c3 = SpecialCategory.objects.create(name="named category2",
                special_name="special2")

        ci1 = CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.filter(category__specialcategory__isnull=False)
        self.assertEqual(qs.count(), 2)
        self.assertQuerysetEqual(qs, [ci2.pk, ci3.pk], lambda x: x.pk, False)

    def test_ticket15316_exclude_false(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(name="named category1",
                special_name="special1")
        c3 = SpecialCategory.objects.create(name="named category2",
                special_name="special2")

        ci1 = CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.exclude(category__specialcategory__isnull=False)
        self.assertEqual(qs.count(), 1)
        self.assertQuerysetEqual(qs, [ci1.pk], lambda x: x.pk)

    def test_ticket15316_filter_true(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(name="named category1",
                special_name="special1")
        c3 = SpecialCategory.objects.create(name="named category2",
                special_name="special2")

        ci1 = CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.filter(category__specialcategory__isnull=True)
        self.assertEqual(qs.count(), 1)
        self.assertQuerysetEqual(qs, [ci1.pk], lambda x: x.pk)

    def test_ticket15316_exclude_true(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(name="named category1",
                special_name="special1")
        c3 = SpecialCategory.objects.create(name="named category2",
                special_name="special2")

        ci1 = CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.exclude(category__specialcategory__isnull=True)
        self.assertEqual(qs.count(), 2)
        self.assertQuerysetEqual(qs, [ci2.pk, ci3.pk], lambda x: x.pk, False)

    def test_ticket15316_one2one_filter_false(self):
        c  = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        c2 = OneToOneCategory.objects.create(category = c1, new_name="new1")
        c3 = OneToOneCategory.objects.create(category = c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.filter(category__onetoonecategory__isnull=False)
        self.assertEqual(qs.count(), 2)
        self.assertQuerysetEqual(qs, [ci2.pk, ci3.pk], lambda x: x.pk, False)

    def test_ticket15316_one2one_exclude_false(self):
        c  = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        c2 = OneToOneCategory.objects.create(category = c1, new_name="new1")
        c3 = OneToOneCategory.objects.create(category = c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.exclude(category__onetoonecategory__isnull=False)
        self.assertEqual(qs.count(), 1)
        self.assertQuerysetEqual(qs, [ci1.pk], lambda x: x.pk)

    def test_ticket15316_one2one_filter_true(self):
        c  = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        c2 = OneToOneCategory.objects.create(category = c1, new_name="new1")
        c3 = OneToOneCategory.objects.create(category = c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.filter(category__onetoonecategory__isnull=True)
        self.assertEqual(qs.count(), 1)
        self.assertQuerysetEqual(qs, [ci1.pk], lambda x: x.pk)

    def test_ticket15316_one2one_exclude_true(self):
        c  = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        c2 = OneToOneCategory.objects.create(category = c1, new_name="new1")
        c3 = OneToOneCategory.objects.create(category = c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.exclude(category__onetoonecategory__isnull=True)
        self.assertEqual(qs.count(), 2)
        self.assertQuerysetEqual(qs, [ci2.pk, ci3.pk], lambda x: x.pk, False)


class Queries5Tests(TestCase):
    def setUp(self):
        # Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the
        # Meta.ordering will be rank3, rank2, rank1.
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
            [d['rank'] for d in dicts],
            [2, 1, 3]
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
        # Test different empty excludes.
        self.assertQuerysetEqual(
            Note.objects.exclude(Q()),
            ['<Note: n1>', '<Note: n2>']
        )
        self.assertQuerysetEqual(
            Note.objects.filter(~Q()),
            ['<Note: n1>', '<Note: n2>']
        )
        self.assertQuerysetEqual(
            Note.objects.filter(~Q()|~Q()),
            ['<Note: n1>', '<Note: n2>']
        )
        self.assertQuerysetEqual(
            Note.objects.exclude(~Q()&~Q()),
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
        Plaything.objects.create(name="p1")
        self.assertQuerysetEqual(
            Plaything.objects.all(),
            ['<Plaything: p1>']
        )

    def test_join_already_in_query(self):
        # Ordering by model related to nullable relations should not change
        # the join type of already existing joins.
        Plaything.objects.create(name="p1")
        s = SingleObject.objects.create(name='s')
        r = RelatedObject.objects.create(single=s, f=1)
        Plaything.objects.create(name="p2", others=r)
        qs = Plaything.objects.all().filter(others__isnull=False).order_by('pk')
        self.assertTrue('JOIN' not in str(qs.query))
        qs = Plaything.objects.all().filter(others__f__isnull=False).order_by('pk')
        self.assertTrue('INNER' in str(qs.query))
        qs = qs.order_by('others__single__name')
        # The ordering by others__single__pk will add one new join (to single)
        # and that join must be LEFT join. The already existing join to related
        # objects must be kept INNER. So, we have both a INNER and a LEFT join
        # in the query.
        self.assertEqual(str(qs.query).count('LEFT'), 1)
        self.assertEqual(str(qs.query).count('INNER'), 1)
        self.assertQuerysetEqual(
            qs,
            ['<Plaything: p2>']
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

    # This next test used to cause really weird PostgreSQL behavior, but it was
    # only apparent much later when the full test suite ran.
    #  - Yeah, it leaves global ITER_CHUNK_SIZE to 2 instead of 100...
    #@unittest.expectedFailure
    def test_slicing_and_cache_interaction(self):
        # We can do slicing beyond what is currently in the result cache,
        # too.

        # We need to mess with the implementation internals a bit here to decrease the
        # cache fill size so that we don't read all the results at once.
        from django.db.models import query
        query.ITER_CHUNK_SIZE = 2
        qs = Tag.objects.all()

        # Fill the cache with the first chunk.
        self.assertTrue(bool(qs))
        self.assertEqual(len(qs._result_cache), 2)

        # Query beyond the end of the cache and check that it is filled out as required.
        self.assertEqual(repr(qs[4]), '<Tag: t5>')
        self.assertEqual(len(qs._result_cache), 5)

        # But querying beyond the end of the result set will fail.
        self.assertRaises(IndexError, lambda: qs[100])

    def test_parallel_iterators(self):
        # Test that parallel iterators work.
        qs = Tag.objects.all()
        i1, i2 = iter(qs), iter(qs)
        self.assertEqual(repr(next(i1)), '<Tag: t1>')
        self.assertEqual(repr(next(i1)), '<Tag: t2>')
        self.assertEqual(repr(next(i2)), '<Tag: t1>')
        self.assertEqual(repr(next(i2)), '<Tag: t2>')
        self.assertEqual(repr(next(i2)), '<Tag: t3>')
        self.assertEqual(repr(next(i1)), '<Tag: t3>')

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
        # and then optimize the inner query without losing results.
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
        self.assertIsNot(q1, q1.all())


class RawQueriesTests(TestCase):
    def setUp(self):
        n1 = Note.objects.create(note='n1', misc='foo', id=1)

    def test_ticket14729(self):
        # Test representation of raw query with one or few parameters passed as list
        query = "SELECT * FROM queries_note WHERE note = %s"
        params = ['n1']
        qs = Note.objects.raw(query, params=params)
        self.assertEqual(repr(qs), str_prefix("<RawQuerySet: %(_)s'SELECT * FROM queries_note WHERE note = n1'>"))

        query = "SELECT * FROM queries_note WHERE note = %s and misc = %s"
        params = ['n1', 'foo']
        qs = Note.objects.raw(query, params=params)
        self.assertEqual(repr(qs), str_prefix("<RawQuerySet: %(_)s'SELECT * FROM queries_note WHERE note = n1 and misc = foo'>"))


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
            self.assertEqual(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[:2])
            self.assertEqual(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[2:])
            self.assertEqual(set(query.values_list('id', flat=True)), set([1]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connections[DEFAULT_DB_ALIAS].features.allow_sliced_subqueries)

    def test_sliced_delete(self):
        "Delete queries can safely contain sliced subqueries"
        try:
            DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:1]).delete()
            self.assertEqual(set(DumbCategory.objects.values_list('id', flat=True)), set([1,2]))
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
        self.assertEqual(ExtraInfo.objects.filter(note__in=n_list)[0].info, 'good')

    def test_no_model_options_cloning(self):
        """
        Test that cloning a queryset does not get out of hand. While complete
        testing is impossible, this is a sanity check against invalid use of
        deepcopy. refs #16759.
        """
        opts_class = type(Note._meta)
        note_deepcopy = getattr(opts_class, "__deepcopy__", None)
        opts_class.__deepcopy__ = lambda obj, memo: self.fail("Model options shouldn't be cloned.")
        try:
            Note.objects.filter(pk__lte=F('pk') + 1).all()
        finally:
            if note_deepcopy is None:
                delattr(opts_class, "__deepcopy__")
            else:
                opts_class.__deepcopy__ = note_deepcopy

    def test_no_fields_cloning(self):
        """
        Test that cloning a queryset does not get out of hand. While complete
        testing is impossible, this is a sanity check against invalid use of
        deepcopy. refs #16759.
        """
        opts_class = type(Note._meta.get_field_by_name("misc")[0])
        note_deepcopy = getattr(opts_class, "__deepcopy__", None)
        opts_class.__deepcopy__ = lambda obj, memo: self.fail("Model fields shouldn't be cloned")
        try:
            Note.objects.filter(note=F('misc')).all()
        finally:
            if note_deepcopy is None:
                delattr(opts_class, "__deepcopy__")
            else:
                opts_class.__deepcopy__ = note_deepcopy

class EmptyQuerySetTests(TestCase):
    def test_emptyqueryset_values(self):
        # #14366 -- Calling .values() on an empty QuerySet and then cloning
        # that should not cause an error
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

    def test_ticket_19151(self):
        # #19151 -- Calling .values() or .values_list() on an empty QuerySet
        # should return an empty QuerySet and not cause an error.
        q = Author.objects.none()
        self.assertQuerysetEqual(q.values(), [])
        self.assertQuerysetEqual(q.values_list(), [])


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

    def test_empty_resultset_sql(self):
        # ticket #12192
        self.assertNumQueries(0, lambda: list(Number.objects.all()[1:1]))


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


class ConditionalTests(BaseQuerysetTest):
    """Tests whose execution depend on different environment conditions like
    Python version or DB backend features"""

    def setUp(self):
        generic = NamedCategory.objects.create(name="Generic")
        t1 = Tag.objects.create(name='t1', category=generic)
        t2 = Tag.objects.create(name='t2', parent=t1, category=generic)
        t3 = Tag.objects.create(name='t3', parent=t1)
        t4 = Tag.objects.create(name='t4', parent=t3)
        t5 = Tag.objects.create(name='t5', parent=t3)


    # In Python 2.6 beta releases, exceptions raised in __len__ are swallowed
    # (Python issue 1242657), so these cases return an empty list, rather than
    # raising an exception. Not a lot we can do about that, unfortunately, due to
    # the way Python handles list() calls internally. Thus, we skip the tests for
    # Python 2.6.
    @unittest.skipIf(sys.version_info[:2] == (2, 6), "Python version is 2.6")
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
    @skipUnlessDBFeature('requires_explicit_null_ordering_when_grouping')
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
    @skipUnlessDBFeature('supports_1000_query_parameters')
    def test_ticket14244(self):
        # Test that the "in" lookup works with lists of 1000 items or more.
        # The numbers amount is picked to force three different IN batches
        # for Oracle, yet to be less than 2100 parameter limit for MSSQL.
        numbers = range(2050)
        Number.objects.all().delete()
        Number.objects.bulk_create(Number(num=num) for num in numbers)
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
            len(numbers)
        )


class UnionTests(unittest.TestCase):
    """
    Tests for the union of two querysets. Bug #12252.
    """
    def setUp(self):
        objectas = []
        objectbs = []
        objectcs = []
        a_info = ['one', 'two', 'three']
        for name in a_info:
            o = ObjectA(name=name)
            o.save()
            objectas.append(o)
        b_info = [('un', 1, objectas[0]), ('deux', 2, objectas[0]), ('trois', 3, objectas[2])]
        for name, number, objecta in b_info:
            o = ObjectB(name=name, num=number, objecta=objecta)
            o.save()
            objectbs.append(o)
        c_info = [('ein', objectas[2], objectbs[2]), ('zwei', objectas[1], objectbs[1])]
        for name, objecta, objectb in c_info:
            o = ObjectC(name=name, objecta=objecta, objectb=objectb)
            o.save()
            objectcs.append(o)

    def check_union(self, model, Q1, Q2):
        filter = model.objects.filter
        self.assertEqual(set(filter(Q1) | filter(Q2)), set(filter(Q1 | Q2)))
        self.assertEqual(set(filter(Q2) | filter(Q1)), set(filter(Q1 | Q2)))

    def test_A_AB(self):
        Q1 = Q(name='two')
        Q2 = Q(objectb__name='deux')
        self.check_union(ObjectA, Q1, Q2)

    def test_A_AB2(self):
        Q1 = Q(name='two')
        Q2 = Q(objectb__name='deux', objectb__num=2)
        self.check_union(ObjectA, Q1, Q2)

    def test_AB_ACB(self):
        Q1 = Q(objectb__name='deux')
        Q2 = Q(objectc__objectb__name='deux')
        self.check_union(ObjectA, Q1, Q2)

    def test_BAB_BAC(self):
        Q1 = Q(objecta__objectb__name='deux')
        Q2 = Q(objecta__objectc__name='ein')
        self.check_union(ObjectB, Q1, Q2)

    def test_BAB_BACB(self):
        Q1 = Q(objecta__objectb__name='deux')
        Q2 = Q(objecta__objectc__objectb__name='trois')
        self.check_union(ObjectB, Q1, Q2)

    def test_BA_BCA__BAB_BAC_BCA(self):
        Q1 = Q(objecta__name='one', objectc__objecta__name='two')
        Q2 = Q(objecta__objectc__name='ein', objectc__objecta__name='three', objecta__objectb__name='trois')
        self.check_union(ObjectB, Q1, Q2)


class DefaultValuesInsertTest(TestCase):
    def test_no_extra_params(self):
        # Ticket #17056 -- affects Oracle
        try:
            DumbCategory.objects.create()
        except TypeError:
            self.fail("Creation of an instance of a model with only the PK field shouldn't error out after bulk insert refactoring (#17056)")

class ExcludeTest(TestCase):
    def setUp(self):
        f1 = Food.objects.create(name='apples')
        Food.objects.create(name='oranges')
        Eaten.objects.create(food=f1, meal='dinner')
        j1 = Job.objects.create(name='Manager')
        r1 = Responsibility.objects.create(description='Playing golf')
        j2 = Job.objects.create(name='Programmer')
        r2 = Responsibility.objects.create(description='Programming')
        JobResponsibilities.objects.create(job=j1, responsibility=r1)
        JobResponsibilities.objects.create(job=j2, responsibility=r2)

    def test_to_field(self):
        self.assertQuerysetEqual(
            Food.objects.exclude(eaten__meal='dinner'),
            ['<Food: oranges>'])
        self.assertQuerysetEqual(
            Job.objects.exclude(responsibilities__description='Playing golf'),
            ['<Job: Programmer>'])
        self.assertQuerysetEqual(
            Responsibility.objects.exclude(jobs__name='Manager'),
            ['<Responsibility: Programming>'])

class NullInExcludeTest(TestCase):
    def setUp(self):
        NullableName.objects.create(name='i1')
        NullableName.objects.create()

    def test_null_in_exclude_qs(self):
        none_val = '' if connection.features.interprets_empty_strings_as_nulls else None
        self.assertQuerysetEqual(
            NullableName.objects.exclude(name__in=[]),
            ['i1', none_val], attrgetter('name'))
        self.assertQuerysetEqual(
            NullableName.objects.exclude(name__in=['i1']),
            [none_val], attrgetter('name'))
        self.assertQuerysetEqual(
            NullableName.objects.exclude(name__in=['i3']),
            ['i1', none_val], attrgetter('name'))
        inner_qs = NullableName.objects.filter(name='i1').values_list('name')
        self.assertQuerysetEqual(
            NullableName.objects.exclude(name__in=inner_qs),
            [none_val], attrgetter('name'))
        # Check that the inner queryset wasn't executed - it should be turned
        # into subquery above
        self.assertIs(inner_qs._result_cache, None)

    @unittest.expectedFailure
    def test_col_not_in_list_containing_null(self):
        """
        The following case is not handled properly because
        SQL's COL NOT IN (list containing null) handling is too weird to
        abstract away.
        """
        self.assertQuerysetEqual(
            NullableName.objects.exclude(name__in=[None]),
            ['i1'], attrgetter('name'))

class EmptyStringsAsNullTest(TestCase):
    """
    Test that filtering on non-null character fields works as expected.
    The reason for these tests is that Oracle treats '' as NULL, and this
    can cause problems in query construction. Refs #17957.
    """

    def setUp(self):
        self.nc = NamedCategory.objects.create(name='')

    def test_direct_exclude(self):
        self.assertQuerysetEqual(
            NamedCategory.objects.exclude(name__in=['nonexisting']),
            [self.nc.pk], attrgetter('pk')
        )

    def test_joined_exclude(self):
        self.assertQuerysetEqual(
            DumbCategory.objects.exclude(namedcategory__name__in=['nonexisting']),
            [self.nc.pk], attrgetter('pk')
        )

class ProxyQueryCleanupTest(TestCase):
    def test_evaluated_proxy_count(self):
        """
        Test that generating the query string doesn't alter the query's state
        in irreversible ways. Refs #18248.
        """
        ProxyCategory.objects.create()
        qs = ProxyCategory.objects.all()
        self.assertEqual(qs.count(), 1)
        str(qs.query)
        self.assertEqual(qs.count(), 1)

class WhereNodeTest(TestCase):
    class DummyNode(object):
        def as_sql(self, qn, connection):
            return 'dummy', []

    def test_empty_full_handling_conjunction(self):
        qn = connection.ops.quote_name
        w = WhereNode(children=[EverythingNode()])
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w.negate()
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w = WhereNode(children=[NothingNode()])
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w = WhereNode(children=[EverythingNode(), EverythingNode()])
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w.negate()
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w = WhereNode(children=[EverythingNode(), self.DummyNode()])
        self.assertEqual(w.as_sql(qn, connection), ('dummy', []))
        w = WhereNode(children=[self.DummyNode(), self.DummyNode()])
        self.assertEqual(w.as_sql(qn, connection), ('(dummy AND dummy)', []))
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('NOT (dummy AND dummy)', []))
        w = WhereNode(children=[NothingNode(), self.DummyNode()])
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('', []))

    def test_empty_full_handling_disjunction(self):
        qn = connection.ops.quote_name
        w = WhereNode(children=[EverythingNode()], connector='OR')
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w.negate()
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w = WhereNode(children=[NothingNode()], connector='OR')
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w = WhereNode(children=[EverythingNode(), EverythingNode()], connector='OR')
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w.negate()
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w = WhereNode(children=[EverythingNode(), self.DummyNode()], connector='OR')
        self.assertEqual(w.as_sql(qn, connection), ('', []))
        w.negate()
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)
        w = WhereNode(children=[self.DummyNode(), self.DummyNode()], connector='OR')
        self.assertEqual(w.as_sql(qn, connection), ('(dummy OR dummy)', []))
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('NOT (dummy OR dummy)', []))
        w = WhereNode(children=[NothingNode(), self.DummyNode()], connector='OR')
        self.assertEqual(w.as_sql(qn, connection), ('dummy', []))
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), ('NOT (dummy)', []))

    def test_empty_nodes(self):
        qn = connection.ops.quote_name
        empty_w = WhereNode()
        w = WhereNode(children=[empty_w, empty_w])
        self.assertEqual(w.as_sql(qn, connection), (None, []))
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), (None, []))
        w.connector = 'OR'
        self.assertEqual(w.as_sql(qn, connection), (None, []))
        w.negate()
        self.assertEqual(w.as_sql(qn, connection), (None, []))
        w = WhereNode(children=[empty_w, NothingNode()], connector='OR')
        self.assertRaises(EmptyResultSet, w.as_sql, qn, connection)

class NullJoinPromotionOrTest(TestCase):
    def setUp(self):
        d = ModelD.objects.create(name='foo')
        ModelA.objects.create(name='bar', d=d)

    def test_ticket_17886(self):
        # The first Q-object is generating the match, the rest of the filters
        # should not remove the match even if they do not match anything. The
        # problem here was that b__name generates a LOUTER JOIN, then
        # b__c__name generates join to c, which the ORM tried to promote but
        # failed as that join isn't nullable.
        q_obj =  (
            Q(d__name='foo')|
            Q(b__name='foo')|
            Q(b__c__name='foo')
        )
        qset = ModelA.objects.filter(q_obj)
        self.assertEqual(len(qset), 1)
        # We generate one INNER JOIN to D. The join is direct and not nullable
        # so we can use INNER JOIN for it. However, we can NOT use INNER JOIN
        # for the b->c join, as a->b is nullable.
        self.assertEqual(str(qset.query).count('INNER JOIN'), 1)

class ReverseJoinTrimmingTest(TestCase):
    def test_reverse_trimming(self):
        # Check that we don't accidentally trim reverse joins - we can't know
        # if there is anything on the other side of the join, so trimming
        # reverse joins can't be done, ever.
        t = Tag.objects.create()
        qs = Tag.objects.filter(annotation__tag=t.pk)
        self.assertIn('INNER JOIN', str(qs.query))
        self.assertEqual(list(qs), [])

class JoinReuseTest(TestCase):
    """
    Test that the queries reuse joins sensibly (for example, direct joins
    are always reused).
    """
    def test_fk_reuse(self):
        qs = Annotation.objects.filter(tag__name='foo').filter(tag__name='bar')
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_fk_reuse_select_related(self):
        qs = Annotation.objects.filter(tag__name='foo').select_related('tag')
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_fk_reuse_annotation(self):
        qs = Annotation.objects.filter(tag__name='foo').annotate(cnt=Count('tag__name'))
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_fk_reuse_disjunction(self):
        qs = Annotation.objects.filter(Q(tag__name='foo') | Q(tag__name='bar'))
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_fk_reuse_order_by(self):
        qs = Annotation.objects.filter(tag__name='foo').order_by('tag__name')
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_revo2o_reuse(self):
        qs = Detail.objects.filter(member__name='foo').filter(member__name='foo')
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_revfk_noreuse(self):
        qs = Author.objects.filter(report__name='r4').filter(report__name='r1')
        self.assertEqual(str(qs.query).count('JOIN'), 2)

class DisjunctionPromotionTests(TestCase):
    def test_disjunction_promotion1(self):
        # Pre-existing join, add two ORed filters to the same join,
        # all joins can be INNER JOINS.
        qs = BaseA.objects.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        qs = qs.filter(Q(b__f1='foo') | Q(b__f2='foo'))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 2)
        # Reverse the order of AND and OR filters.
        qs = BaseA.objects.filter(Q(b__f1='foo') | Q(b__f2='foo'))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        qs = qs.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 2)

    def test_disjunction_promotion2(self):
        qs = BaseA.objects.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        # Now we have two different joins in an ORed condition, these
        # must be OUTER joins. The pre-existing join should remain INNER.
        qs = qs.filter(Q(b__f1='foo') | Q(c__f2='foo'))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 2)
        # Reverse case.
        qs = BaseA.objects.filter(Q(b__f1='foo') | Q(c__f2='foo'))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 2)
        qs = qs.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 2)

    def test_disjunction_promotion3(self):
        qs = BaseA.objects.filter(a__f2='bar')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        # The ANDed a__f2 filter allows us to use keep using INNER JOIN
        # even inside the ORed case. If the join to a__ returns nothing,
        # the ANDed filter for a__f2 can't be true.
        qs = qs.filter(Q(a__f1='foo') | Q(b__f2='foo'))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)

    @unittest.expectedFailure
    def test_disjunction_promotion3_failing(self):
        # Now the ORed filter creates LOUTER join, but we do not have
        # logic to unpromote it for the AND filter after it. The query
        # results will be correct, but we have one LOUTER JOIN too much
        # currently.
        qs = BaseA.objects.filter(
            Q(a__f1='foo') | Q(b__f2='foo')).filter(a__f2='bar')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)

    def test_disjunction_promotion4(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('JOIN'), 0)
        qs = qs.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        qs = BaseA.objects.filter(a__f1='foo')
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        qs = qs.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)

    def test_disjunction_promotion5(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        # Note that the above filters on a force the join to an
        # inner join even if it is trimmed.
        self.assertEqual(str(qs.query).count('JOIN'), 0)
        qs = qs.filter(Q(a__f1='foo') | Q(b__f1='foo'))
        # So, now the a__f1 join doesn't need promotion.
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)

    @unittest.expectedFailure
    def test_disjunction_promotion5_failing(self):
        qs = BaseA.objects.filter(Q(a__f1='foo') | Q(b__f1='foo'))
        # Now the join to a is created as LOUTER
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 0)
        # The below filter should force the a to be inner joined. But,
        # this is failing as we do not have join unpromotion logic.
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)

    def test_disjunction_promotion6(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('JOIN'), 0)
        qs = BaseA.objects.filter(Q(a__f1='foo') & Q(b__f1='foo'))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 2)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 0)

        qs = BaseA.objects.filter(Q(a__f1='foo') & Q(b__f1='foo'))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 0)
        self.assertEqual(str(qs.query).count('INNER JOIN'), 2)
        qs = qs.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 2)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 0)

    def test_disjunction_promotion7(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count('JOIN'), 0)
        qs = BaseA.objects.filter(Q(a__f1='foo') | (Q(b__f1='foo') & Q(a__f1='bar')))
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)
        qs = BaseA.objects.filter(
            (Q(a__f1='foo') | Q(b__f1='foo')) & (Q(a__f1='bar') | Q(c__f1='foo'))
        )
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 3)
        self.assertEqual(str(qs.query).count('INNER JOIN'), 0)
        qs = BaseA.objects.filter(
            (Q(a__f1='foo') | (Q(a__f1='bar')) & (Q(b__f1='bar') | Q(c__f1='foo')))
        )
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 2)
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)

    def test_disjunction_promotion_fexpression(self):
        qs = BaseA.objects.filter(Q(a__f1=F('b__f1')) | Q(b__f1='foo'))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 1)
        self.assertEqual(str(qs.query).count('INNER JOIN'), 1)
        qs = BaseA.objects.filter(Q(a__f1=F('c__f1')) | Q(b__f1='foo'))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 3)
        qs = BaseA.objects.filter(Q(a__f1=F('b__f1')) | Q(a__f2=F('b__f2')) | Q(c__f1='foo'))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 3)
        qs = BaseA.objects.filter(Q(a__f1=F('c__f1')) | (Q(pk=1) & Q(pk=2)))
        self.assertEqual(str(qs.query).count('LEFT OUTER JOIN'), 2)
        self.assertEqual(str(qs.query).count('INNER JOIN'), 0)
