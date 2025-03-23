import datetime
import pickle
import sys
import unittest
from operator import attrgetter

from django.core.exceptions import EmptyResultSet, FieldError, FullResultSet
from django.db import DEFAULT_DB_ALIAS, connection
from django.db.models import CharField, Count, Exists, F, Max, OuterRef, Q
from django.db.models.expressions import RawSQL
from django.db.models.functions import ExtractYear, Length, LTrim
from django.db.models.sql.constants import LOUTER
from django.db.models.sql.where import AND, OR, NothingNode, WhereNode
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext, register_lookup

from .models import (
    FK1,
    Annotation,
    Article,
    Author,
    BaseA,
    BaseUser,
    Book,
    CategoryItem,
    CategoryRelationship,
    Celebrity,
    Channel,
    Chapter,
    Child,
    ChildObjectA,
    Classroom,
    CommonMixedCaseForeignKeys,
    Company,
    Cover,
    CustomPk,
    CustomPkTag,
    DateTimePK,
    Detail,
    DumbCategory,
    Eaten,
    Employment,
    ExtraInfo,
    Fan,
    Food,
    Identifier,
    Individual,
    Item,
    Job,
    JobResponsibilities,
    Join,
    LeafA,
    LeafB,
    LoopX,
    LoopZ,
    ManagedModel,
    Member,
    MixedCaseDbColumnCategoryItem,
    MixedCaseFieldCategoryItem,
    ModelA,
    ModelB,
    ModelC,
    ModelD,
    MyObject,
    NamedCategory,
    Node,
    Note,
    NullableName,
    Number,
    ObjectA,
    ObjectB,
    ObjectC,
    OneToOneCategory,
    Order,
    OrderItem,
    Page,
    Paragraph,
    Person,
    Plaything,
    PointerA,
    Program,
    ProxyCategory,
    ProxyObjectA,
    ProxyObjectB,
    Ranking,
    Related,
    RelatedIndividual,
    RelatedObject,
    Report,
    ReportComment,
    ReservedName,
    Responsibility,
    School,
    SharedConnection,
    SimpleCategory,
    SingleObject,
    SpecialCategory,
    Staff,
    StaffUser,
    Student,
    Tag,
    Task,
    Teacher,
    Ticket21203Child,
    Ticket21203Parent,
    Ticket23605A,
    Ticket23605B,
    Ticket23605C,
    TvChef,
    Valid,
    X,
)


class UnpickleableError(Exception):
    def __reduce__(self):
        raise type(self)("Cannot pickle.")


class Queries1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nc1 = generic = NamedCategory.objects.create(name="Generic")
        cls.t1 = Tag.objects.create(name="t1", category=generic)
        cls.t2 = Tag.objects.create(name="t2", parent=cls.t1, category=generic)
        cls.t3 = Tag.objects.create(name="t3", parent=cls.t1)
        cls.t4 = Tag.objects.create(name="t4", parent=cls.t3)
        cls.t5 = Tag.objects.create(name="t5", parent=cls.t3)

        cls.n1 = Note.objects.create(note="n1", misc="foo", id=1)
        cls.n2 = Note.objects.create(note="n2", misc="bar", id=2)
        cls.n3 = Note.objects.create(note="n3", misc="foo", id=3, negate=False)

        cls.ann1 = Annotation.objects.create(name="a1", tag=cls.t1)
        cls.ann1.notes.add(cls.n1)
        ann2 = Annotation.objects.create(name="a2", tag=cls.t4)
        ann2.notes.add(cls.n2, cls.n3)

        # Create these out of order so that sorting by 'id' will be different to sorting
        # by 'info'. Helps detect some problems later.
        cls.e2 = ExtraInfo.objects.create(
            info="e2", note=cls.n2, value=41, filterable=False
        )
        e1 = ExtraInfo.objects.create(info="e1", note=cls.n1, value=42)

        cls.a1 = Author.objects.create(name="a1", num=1001, extra=e1)
        cls.a2 = Author.objects.create(name="a2", num=2002, extra=e1)
        cls.a3 = Author.objects.create(name="a3", num=3003, extra=cls.e2)
        cls.a4 = Author.objects.create(name="a4", num=4004, extra=cls.e2)

        cls.time1 = datetime.datetime(2007, 12, 19, 22, 25, 0)
        cls.time2 = datetime.datetime(2007, 12, 19, 21, 0, 0)
        time3 = datetime.datetime(2007, 12, 20, 22, 25, 0)
        time4 = datetime.datetime(2007, 12, 20, 21, 0, 0)
        cls.i1 = Item.objects.create(
            name="one",
            created=cls.time1,
            modified=cls.time1,
            creator=cls.a1,
            note=cls.n3,
        )
        cls.i1.tags.set([cls.t1, cls.t2])
        cls.i2 = Item.objects.create(
            name="two", created=cls.time2, creator=cls.a2, note=cls.n2
        )
        cls.i2.tags.set([cls.t1, cls.t3])
        cls.i3 = Item.objects.create(
            name="three", created=time3, creator=cls.a2, note=cls.n3
        )
        cls.i4 = Item.objects.create(
            name="four", created=time4, creator=cls.a4, note=cls.n3
        )
        cls.i4.tags.set([cls.t4])

        cls.r1 = Report.objects.create(name="r1", creator=cls.a1)
        cls.r2 = Report.objects.create(name="r2", creator=cls.a3)
        cls.r3 = Report.objects.create(name="r3")

        # Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the Meta.ordering
        # will be rank3, rank2, rank1.
        cls.rank1 = Ranking.objects.create(rank=2, author=cls.a2)

        cls.c1 = Cover.objects.create(title="first", item=cls.i4)
        cls.c2 = Cover.objects.create(title="second", item=cls.i2)

    def test_subquery_condition(self):
        qs1 = Tag.objects.filter(pk__lte=0)
        qs2 = Tag.objects.filter(parent__in=qs1)
        qs3 = Tag.objects.filter(parent__in=qs2)
        self.assertEqual(qs3.query.subq_aliases, {"T", "U", "V"})
        self.assertIn("v0", str(qs3.query).lower())
        qs4 = qs3.filter(parent__in=qs1)
        self.assertEqual(qs4.query.subq_aliases, {"T", "U", "V"})
        # It is possible to reuse U for the second subquery, no need to use W.
        self.assertNotIn("w0", str(qs4.query).lower())
        # So, 'U0."id"' is referenced in SELECT and WHERE twice.
        self.assertEqual(str(qs4.query).lower().count("u0."), 4)

    def test_ticket1050(self):
        self.assertSequenceEqual(
            Item.objects.filter(tags__isnull=True),
            [self.i3],
        )
        self.assertSequenceEqual(
            Item.objects.filter(tags__id__isnull=True),
            [self.i3],
        )

    def test_ticket1801(self):
        self.assertSequenceEqual(
            Author.objects.filter(item=self.i2),
            [self.a2],
        )
        self.assertSequenceEqual(
            Author.objects.filter(item=self.i3),
            [self.a2],
        )
        self.assertSequenceEqual(
            Author.objects.filter(item=self.i2) & Author.objects.filter(item=self.i3),
            [self.a2],
        )

    def test_ticket2306(self):
        # Checking that no join types are "left outer" joins.
        query = Item.objects.filter(tags=self.t2).query
        self.assertNotIn(LOUTER, [x.join_type for x in query.alias_map.values()])

        self.assertSequenceEqual(
            Item.objects.filter(Q(tags=self.t1)).order_by("name"),
            [self.i1, self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.filter(Q(tags=self.t1)).filter(Q(tags=self.t2)),
            [self.i1],
        )
        self.assertSequenceEqual(
            Item.objects.filter(Q(tags=self.t1)).filter(
                Q(creator__name="fred") | Q(tags=self.t2)
            ),
            [self.i1],
        )

        # Each filter call is processed "at once" against a single table, so this is
        # different from the previous example as it tries to find tags that are two
        # things at once (rather than two tags).
        self.assertSequenceEqual(
            Item.objects.filter(Q(tags=self.t1) & Q(tags=self.t2)), []
        )
        self.assertSequenceEqual(
            Item.objects.filter(
                Q(tags=self.t1), Q(creator__name="fred") | Q(tags=self.t2)
            ),
            [],
        )

        qs = Author.objects.filter(ranking__rank=2, ranking__id=self.rank1.id)
        self.assertSequenceEqual(list(qs), [self.a2])
        self.assertEqual(2, qs.query.count_active_tables(), 2)
        qs = Author.objects.filter(ranking__rank=2).filter(ranking__id=self.rank1.id)
        self.assertEqual(qs.query.count_active_tables(), 3)

    def test_ticket4464(self):
        self.assertSequenceEqual(
            Item.objects.filter(tags=self.t1).filter(tags=self.t2),
            [self.i1],
        )
        self.assertSequenceEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2])
            .distinct()
            .order_by("name"),
            [self.i1, self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).filter(tags=self.t3),
            [self.i2],
        )

        # Make sure .distinct() works with slicing (this was broken in Oracle).
        self.assertSequenceEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2]).order_by("name")[:3],
            [self.i1, self.i1, self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.filter(tags__in=[self.t1, self.t2])
            .distinct()
            .order_by("name")[:3],
            [self.i1, self.i2],
        )

    def test_tickets_2080_3592(self):
        self.assertSequenceEqual(
            Author.objects.filter(item__name="one") | Author.objects.filter(name="a3"),
            [self.a1, self.a3],
        )
        self.assertSequenceEqual(
            Author.objects.filter(Q(item__name="one") | Q(name="a3")),
            [self.a1, self.a3],
        )
        self.assertSequenceEqual(
            Author.objects.filter(Q(name="a3") | Q(item__name="one")),
            [self.a1, self.a3],
        )
        self.assertSequenceEqual(
            Author.objects.filter(Q(item__name="three") | Q(report__name="r3")),
            [self.a2],
        )

    def test_ticket6074(self):
        # Merging two empty result sets shouldn't leave a queryset with no constraints
        # (which would match everything).
        self.assertSequenceEqual(Author.objects.filter(Q(id__in=[])), [])
        self.assertSequenceEqual(Author.objects.filter(Q(id__in=[]) | Q(id__in=[])), [])

    def test_tickets_1878_2939(self):
        self.assertEqual(Item.objects.values("creator").distinct().count(), 3)

        # Create something with a duplicate 'name' so that we can test multi-column
        # cases (which require some tricky SQL transformations under the covers).
        xx = Item(name="four", created=self.time1, creator=self.a2, note=self.n1)
        xx.save()
        self.assertEqual(
            Item.objects.exclude(name="two")
            .values("creator", "name")
            .distinct()
            .count(),
            4,
        )
        self.assertEqual(
            (
                Item.objects.exclude(name="two")
                .extra(select={"foo": "%s"}, select_params=(1,))
                .values("creator", "name", "foo")
                .distinct()
                .count()
            ),
            4,
        )
        self.assertEqual(
            (
                Item.objects.exclude(name="two")
                .extra(select={"foo": "%s"}, select_params=(1,))
                .values("creator", "name")
                .distinct()
                .count()
            ),
            4,
        )
        xx.delete()

    def test_ticket7323(self):
        self.assertEqual(Item.objects.values("creator", "name").count(), 4)

    def test_ticket2253(self):
        q1 = Item.objects.order_by("name")
        q2 = Item.objects.filter(id=self.i1.id)
        self.assertSequenceEqual(q1, [self.i4, self.i1, self.i3, self.i2])
        self.assertSequenceEqual(q2, [self.i1])
        self.assertSequenceEqual(
            (q1 | q2).order_by("name"),
            [self.i4, self.i1, self.i3, self.i2],
        )
        self.assertSequenceEqual((q1 & q2).order_by("name"), [self.i1])

        q1 = Item.objects.filter(tags=self.t1)
        q2 = Item.objects.filter(note=self.n3, tags=self.t2)
        q3 = Item.objects.filter(creator=self.a4)
        self.assertSequenceEqual(
            ((q1 & q2) | q3).order_by("name"),
            [self.i4, self.i1],
        )

    def test_order_by_tables(self):
        q1 = Item.objects.order_by("name")
        q2 = Item.objects.filter(id=self.i1.id)
        list(q2)
        combined_query = (q1 & q2).order_by("name").query
        self.assertEqual(
            len(
                [
                    t
                    for t in combined_query.alias_map
                    if combined_query.alias_refcount[t]
                ]
            ),
            1,
        )

    def test_order_by_join_unref(self):
        """
        This test is related to the above one, testing that there aren't
        old JOINs in the query.
        """
        qs = Celebrity.objects.order_by("greatest_fan__fan_of")
        self.assertIn("OUTER JOIN", str(qs.query))
        qs = qs.order_by("id")
        self.assertNotIn("OUTER JOIN", str(qs.query))

    def test_order_by_related_field_transform(self):
        extra_12 = ExtraInfo.objects.create(
            info="extra 12",
            date=DateTimePK.objects.create(date=datetime.datetime(2021, 12, 10)),
        )
        extra_11 = ExtraInfo.objects.create(
            info="extra 11",
            date=DateTimePK.objects.create(date=datetime.datetime(2022, 11, 10)),
        )
        self.assertSequenceEqual(
            ExtraInfo.objects.filter(date__isnull=False).order_by("date__month"),
            [extra_11, extra_12],
        )

    def test_filter_by_related_field_transform(self):
        extra_old = ExtraInfo.objects.create(
            info="extra 12",
            date=DateTimePK.objects.create(date=datetime.datetime(2020, 12, 10)),
        )
        ExtraInfo.objects.create(info="extra 11", date=DateTimePK.objects.create())
        a5 = Author.objects.create(name="a5", num=5005, extra=extra_old)

        fk_field = ExtraInfo._meta.get_field("date")
        with register_lookup(fk_field, ExtractYear):
            self.assertSequenceEqual(
                ExtraInfo.objects.filter(date__year=2020),
                [extra_old],
            )
            self.assertSequenceEqual(
                Author.objects.filter(extra__date__year=2020), [a5]
            )

    def test_filter_by_related_field_nested_transforms(self):
        extra = ExtraInfo.objects.create(info=" extra")
        a5 = Author.objects.create(name="a5", num=5005, extra=extra)
        info_field = ExtraInfo._meta.get_field("info")
        with register_lookup(info_field, Length), register_lookup(CharField, LTrim):
            self.assertSequenceEqual(
                Author.objects.filter(extra__info__ltrim__length=5), [a5]
            )

    def test_get_clears_ordering(self):
        """
        get() should clear ordering for optimization purposes.
        """
        with CaptureQueriesContext(connection) as captured_queries:
            Author.objects.order_by("name").get(pk=self.a1.pk)
        self.assertNotIn("order by", captured_queries[0]["sql"].lower())

    def test_tickets_4088_4306(self):
        self.assertSequenceEqual(Report.objects.filter(creator=1001), [self.r1])
        self.assertSequenceEqual(Report.objects.filter(creator__num=1001), [self.r1])
        self.assertSequenceEqual(Report.objects.filter(creator__id=1001), [])
        self.assertSequenceEqual(
            Report.objects.filter(creator__id=self.a1.id), [self.r1]
        )
        self.assertSequenceEqual(Report.objects.filter(creator__name="a1"), [self.r1])

    def test_ticket4510(self):
        self.assertSequenceEqual(
            Author.objects.filter(report__name="r1"),
            [self.a1],
        )

    def test_ticket7378(self):
        self.assertSequenceEqual(self.a1.report_set.all(), [self.r1])

    def test_tickets_5324_6704(self):
        self.assertSequenceEqual(
            Item.objects.filter(tags__name="t4"),
            [self.i4],
        )
        self.assertSequenceEqual(
            Item.objects.exclude(tags__name="t4").order_by("name").distinct(),
            [self.i1, self.i3, self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.exclude(tags__name="t4").order_by("name").distinct().reverse(),
            [self.i2, self.i3, self.i1],
        )
        self.assertSequenceEqual(
            Author.objects.exclude(item__name="one").distinct().order_by("name"),
            [self.a2, self.a3, self.a4],
        )

        # Excluding across a m2m relation when there is more than one related
        # object associated was problematic.
        self.assertSequenceEqual(
            Item.objects.exclude(tags__name="t1").order_by("name"),
            [self.i4, self.i3],
        )
        self.assertSequenceEqual(
            Item.objects.exclude(tags__name="t1").exclude(tags__name="t4"),
            [self.i3],
        )

        # Excluding from a relation that cannot be NULL should not use outer joins.
        query = Item.objects.exclude(creator__in=[self.a1, self.a2]).query
        self.assertNotIn(LOUTER, [x.join_type for x in query.alias_map.values()])

        # Similarly, when one of the joins cannot possibly, ever, involve NULL
        # values (Author -> ExtraInfo, in the following), it should never be
        # promoted to a left outer join. So the following query should only
        # involve one "left outer" join (Author -> Item is 0-to-many).
        qs = Author.objects.filter(id=self.a1.id).filter(
            Q(extra__note=self.n1) | Q(item__note=self.n3)
        )
        self.assertEqual(
            len(
                [
                    x
                    for x in qs.query.alias_map.values()
                    if x.join_type == LOUTER and qs.query.alias_refcount[x.table_alias]
                ]
            ),
            1,
        )

        # The previous changes shouldn't affect nullable foreign key joins.
        self.assertSequenceEqual(
            Tag.objects.filter(parent__isnull=True).order_by("name"), [self.t1]
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(parent__isnull=True).order_by("name"),
            [self.t2, self.t3, self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(Q(parent__name="t1") | Q(parent__isnull=True)).order_by(
                "name"
            ),
            [self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(Q(parent__isnull=True) | Q(parent__name="t1")).order_by(
                "name"
            ),
            [self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(Q(parent__parent__isnull=True)).order_by("name"),
            [self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Tag.objects.filter(~Q(parent__parent__isnull=True)).order_by("name"),
            [self.t4, self.t5],
        )

    def test_ticket2091(self):
        t = Tag.objects.get(name="t4")
        self.assertSequenceEqual(Item.objects.filter(tags__in=[t]), [self.i4])

    def test_avoid_infinite_loop_on_too_many_subqueries(self):
        x = Tag.objects.filter(pk=1)
        local_recursion_limit = sys.getrecursionlimit() // 16
        msg = "Maximum recursion depth exceeded: too many subqueries."
        with self.assertRaisesMessage(RecursionError, msg):
            for i in range(local_recursion_limit + 2):
                x = Tag.objects.filter(pk__in=x)

    def test_reasonable_number_of_subq_aliases(self):
        x = Tag.objects.filter(pk=1)
        for _ in range(20):
            x = Tag.objects.filter(pk__in=x)
        self.assertEqual(
            x.query.subq_aliases,
            {
                "T",
                "U",
                "V",
                "W",
                "X",
                "Y",
                "Z",
                "AA",
                "AB",
                "AC",
                "AD",
                "AE",
                "AF",
                "AG",
                "AH",
                "AI",
                "AJ",
                "AK",
                "AL",
                "AM",
                "AN",
            },
        )

    def test_heterogeneous_qs_combination(self):
        # Combining querysets built on different models should behave in a well-defined
        # fashion. We raise an error.
        msg = "Cannot combine queries on two different base models."
        with self.assertRaisesMessage(TypeError, msg):
            Author.objects.all() & Tag.objects.all()
        with self.assertRaisesMessage(TypeError, msg):
            Author.objects.all() | Tag.objects.all()

    def test_ticket3141(self):
        self.assertEqual(Author.objects.extra(select={"foo": "1"}).count(), 4)
        self.assertEqual(
            Author.objects.extra(select={"foo": "%s"}, select_params=(1,)).count(), 4
        )

    def test_ticket2400(self):
        self.assertSequenceEqual(
            Author.objects.filter(item__isnull=True),
            [self.a3],
        )
        self.assertSequenceEqual(
            Tag.objects.filter(item__isnull=True),
            [self.t5],
        )

    def test_ticket2496(self):
        self.assertSequenceEqual(
            Item.objects.extra(tables=["queries_author"])
            .select_related()
            .order_by("name")[:1],
            [self.i4],
        )

    def test_error_raised_on_filter_with_dictionary(self):
        with self.assertRaisesMessage(FieldError, "Cannot parse keyword query as dict"):
            Note.objects.filter({"note": "n1", "misc": "foo"})

    def test_tickets_2076_7256(self):
        # Ordering on related tables should be possible, even if the table is
        # not otherwise involved.
        self.assertSequenceEqual(
            Item.objects.order_by("note__note", "name"),
            [self.i2, self.i4, self.i1, self.i3],
        )

        # Ordering on a related field should use the remote model's default
        # ordering as a final step.
        self.assertSequenceEqual(
            Author.objects.order_by("extra", "-name"),
            [self.a2, self.a1, self.a4, self.a3],
        )

        # Using remote model default ordering can span multiple models (in this
        # case, Cover is ordered by Item's default, which uses Note's default).
        self.assertSequenceEqual(Cover.objects.all(), [self.c1, self.c2])

        # If the remote model does not have a default ordering, we order by its 'id'
        # field.
        self.assertSequenceEqual(
            Item.objects.order_by("creator", "name"),
            [self.i1, self.i3, self.i2, self.i4],
        )

        # Ordering by a many-valued attribute (e.g. a many-to-many or reverse
        # ForeignKey) is legal, but the results might not make sense. That
        # isn't Django's problem. Garbage in, garbage out.
        self.assertSequenceEqual(
            Item.objects.filter(tags__isnull=False).order_by("tags", "id"),
            [self.i1, self.i2, self.i1, self.i2, self.i4],
        )

        # If we replace the default ordering, Django adjusts the required
        # tables automatically. Item normally requires a join with Note to do
        # the default ordering, but that isn't needed here.
        qs = Item.objects.order_by("name")
        self.assertSequenceEqual(qs, [self.i4, self.i1, self.i3, self.i2])
        self.assertEqual(len(qs.query.alias_map), 1)

    def test_tickets_2874_3002(self):
        qs = Item.objects.select_related().order_by("note__note", "name")
        self.assertQuerySetEqual(qs, [self.i2, self.i4, self.i1, self.i3])

        # This is also a good select_related() test because there are multiple
        # Note entries in the SQL. The two Note items should be different.
        self.assertEqual(repr(qs[0].note), "<Note: n2>")
        self.assertEqual(repr(qs[0].creator.extra.note), "<Note: n1>")

    def test_ticket3037(self):
        self.assertSequenceEqual(
            Item.objects.filter(
                Q(creator__name="a3", name="two") | Q(creator__name="a4", name="four")
            ),
            [self.i4],
        )

    def test_tickets_5321_7070(self):
        # Ordering columns must be included in the output columns. Note that
        # this means results that might otherwise be distinct are not (if there
        # are multiple values in the ordering cols), as in this example. This
        # isn't a bug; it's a warning to be careful with the selection of
        # ordering columns.
        self.assertSequenceEqual(
            Note.objects.values("misc").distinct().order_by("note", "-misc"),
            [{"misc": "foo"}, {"misc": "bar"}, {"misc": "foo"}],
        )

    def test_ticket4358(self):
        # If you don't pass any fields to values(), relation fields are
        # returned as "foo_id" keys, not "foo". For consistency, you should be
        # able to pass "foo_id" in the fields list and have it work, too. We
        # actually allow both "foo" and "foo_id".
        # The *_id version is returned by default.
        self.assertIn("note_id", ExtraInfo.objects.values()[0])
        # You can also pass it in explicitly.
        self.assertSequenceEqual(
            ExtraInfo.objects.values("note_id"), [{"note_id": 1}, {"note_id": 2}]
        )
        # ...or use the field name.
        self.assertSequenceEqual(
            ExtraInfo.objects.values("note"), [{"note": 1}, {"note": 2}]
        )

    def test_ticket6154(self):
        # Multiple filter statements are joined using "AND" all the time.

        self.assertSequenceEqual(
            Author.objects.filter(id=self.a1.id).filter(
                Q(extra__note=self.n1) | Q(item__note=self.n3)
            ),
            [self.a1],
        )
        self.assertSequenceEqual(
            Author.objects.filter(
                Q(extra__note=self.n1) | Q(item__note=self.n3)
            ).filter(id=self.a1.id),
            [self.a1],
        )

    def test_ticket6981(self):
        self.assertSequenceEqual(
            Tag.objects.select_related("parent").order_by("name"),
            [self.t1, self.t2, self.t3, self.t4, self.t5],
        )

    def test_ticket9926(self):
        self.assertSequenceEqual(
            Tag.objects.select_related("parent", "category").order_by("name"),
            [self.t1, self.t2, self.t3, self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Tag.objects.select_related("parent", "parent__category").order_by("name"),
            [self.t1, self.t2, self.t3, self.t4, self.t5],
        )

    def test_tickets_6180_6203(self):
        # Dates with limits and/or counts
        self.assertEqual(Item.objects.count(), 4)
        self.assertEqual(Item.objects.datetimes("created", "month").count(), 1)
        self.assertEqual(Item.objects.datetimes("created", "day").count(), 2)
        self.assertEqual(len(Item.objects.datetimes("created", "day")), 2)
        self.assertEqual(
            Item.objects.datetimes("created", "day")[0],
            datetime.datetime(2007, 12, 19, 0, 0),
        )

    def test_tickets_7087_12242(self):
        # Dates with extra select columns
        self.assertSequenceEqual(
            Item.objects.datetimes("created", "day").extra(select={"a": 1}),
            [
                datetime.datetime(2007, 12, 19, 0, 0),
                datetime.datetime(2007, 12, 20, 0, 0),
            ],
        )
        self.assertSequenceEqual(
            Item.objects.extra(select={"a": 1}).datetimes("created", "day"),
            [
                datetime.datetime(2007, 12, 19, 0, 0),
                datetime.datetime(2007, 12, 20, 0, 0),
            ],
        )

        name = "one"
        self.assertSequenceEqual(
            Item.objects.datetimes("created", "day").extra(
                where=["name=%s"], params=[name]
            ),
            [datetime.datetime(2007, 12, 19, 0, 0)],
        )

        self.assertSequenceEqual(
            Item.objects.extra(where=["name=%s"], params=[name]).datetimes(
                "created", "day"
            ),
            [datetime.datetime(2007, 12, 19, 0, 0)],
        )

    def test_ticket7155(self):
        # Nullable dates
        self.assertSequenceEqual(
            Item.objects.datetimes("modified", "day"),
            [datetime.datetime(2007, 12, 19, 0, 0)],
        )

    def test_order_by_rawsql(self):
        self.assertSequenceEqual(
            Item.objects.values("note__note").order_by(
                RawSQL("queries_note.note", ()),
                "id",
            ),
            [
                {"note__note": "n2"},
                {"note__note": "n3"},
                {"note__note": "n3"},
                {"note__note": "n3"},
            ],
        )

    def test_ticket7096(self):
        # Make sure exclude() with multiple conditions continues to work.
        self.assertSequenceEqual(
            Tag.objects.filter(parent=self.t1, name="t3").order_by("name"),
            [self.t3],
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(parent=self.t1, name="t3").order_by("name"),
            [self.t1, self.t2, self.t4, self.t5],
        )
        self.assertSequenceEqual(
            Item.objects.exclude(tags__name="t1", name="one")
            .order_by("name")
            .distinct(),
            [self.i4, self.i3, self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.filter(name__in=["three", "four"])
            .exclude(tags__name="t1")
            .order_by("name"),
            [self.i4, self.i3],
        )

        # More twisted cases, involving nested negations.
        self.assertSequenceEqual(
            Item.objects.exclude(~Q(tags__name="t1", name="one")),
            [self.i1],
        )
        self.assertSequenceEqual(
            Item.objects.filter(~Q(tags__name="t1", name="one"), name="two"),
            [self.i2],
        )
        self.assertSequenceEqual(
            Item.objects.exclude(~Q(tags__name="t1", name="one"), name="two"),
            [self.i4, self.i1, self.i3],
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
        self.assertEqual(query2.get_compiler(qs.db).as_sql()[0], query)

    def test_deferred_load_qs_pickling(self):
        # Check pickling of deferred-loading querysets
        qs = Item.objects.defer("name", "creator")
        q2 = pickle.loads(pickle.dumps(qs))
        self.assertEqual(list(qs), list(q2))
        q3 = pickle.loads(pickle.dumps(qs, pickle.HIGHEST_PROTOCOL))
        self.assertEqual(list(qs), list(q3))

    def test_ticket7277(self):
        self.assertSequenceEqual(
            self.n1.annotation_set.filter(
                Q(tag=self.t5)
                | Q(tag__children=self.t5)
                | Q(tag__children__children=self.t5)
            ),
            [self.ann1],
        )

    def test_tickets_7448_7707(self):
        # Complex objects should be converted to strings before being used in
        # lookups.
        self.assertSequenceEqual(
            Item.objects.filter(created__in=[self.time1, self.time2]),
            [self.i1, self.i2],
        )

    def test_ticket7235(self):
        # An EmptyQuerySet should not raise exceptions if it is filtered.
        Eaten.objects.create(meal="m")
        q = Eaten.objects.none()
        with self.assertNumQueries(0):
            self.assertSequenceEqual(q.all(), [])
            self.assertSequenceEqual(q.filter(meal="m"), [])
            self.assertSequenceEqual(q.exclude(meal="m"), [])
            self.assertSequenceEqual(q.complex_filter({"pk": 1}), [])
            self.assertSequenceEqual(q.select_related("food"), [])
            self.assertSequenceEqual(q.annotate(Count("food")), [])
            self.assertSequenceEqual(q.order_by("meal", "food"), [])
            self.assertSequenceEqual(q.distinct(), [])
            self.assertSequenceEqual(q.extra(select={"foo": "1"}), [])
            self.assertSequenceEqual(q.reverse(), [])
            q.query.low_mark = 1
            msg = "Cannot change a query once a slice has been taken."
            with self.assertRaisesMessage(TypeError, msg):
                q.extra(select={"foo": "1"})
            self.assertSequenceEqual(q.defer("meal"), [])
            self.assertSequenceEqual(q.only("meal"), [])

    def test_ticket7791(self):
        # There were "issues" when ordering and distinct-ing on fields related
        # via ForeignKeys.
        self.assertEqual(len(Note.objects.order_by("extrainfo__info").distinct()), 3)

        # Pickling of QuerySets using datetimes() should work.
        qs = Item.objects.datetimes("created", "month")
        pickle.loads(pickle.dumps(qs))

    def test_ticket9997(self):
        # If a ValuesList or Values queryset is passed as an inner query, we
        # make sure it's only requesting a single value and use that as the
        # thing to select.
        self.assertSequenceEqual(
            Tag.objects.filter(
                name__in=Tag.objects.filter(parent=self.t1).values("name")
            ),
            [self.t2, self.t3],
        )

    def test_ticket9985(self):
        # qs.values_list(...).values(...) combinations should work.
        self.assertSequenceEqual(
            Note.objects.values_list("note", flat=True).values("id").order_by("id"),
            [{"id": 1}, {"id": 2}, {"id": 3}],
        )
        self.assertSequenceEqual(
            Annotation.objects.filter(
                notes__in=Note.objects.filter(note="n1")
                .values_list("note")
                .values("id")
            ),
            [self.ann1],
        )

    def test_ticket10205(self):
        # When bailing out early because of an empty "__in" filter, we need
        # to set things up correctly internally so that subqueries can continue
        # properly.
        self.assertEqual(Tag.objects.filter(name__in=()).update(name="foo"), 0)

    def test_ticket10432(self):
        # Testing an empty "__in" filter with a generator as the value.
        def f():
            return iter([])

        n_obj = Note.objects.all()[0]

        def g():
            yield n_obj.pk

        self.assertSequenceEqual(Note.objects.filter(pk__in=f()), [])
        self.assertEqual(list(Note.objects.filter(pk__in=g())), [n_obj])

    def test_ticket10742(self):
        # Queries used in an __in clause don't execute subqueries

        subq = Author.objects.filter(num__lt=3000)
        qs = Author.objects.filter(pk__in=subq)
        self.assertSequenceEqual(qs, [self.a1, self.a2])

        # The subquery result cache should not be populated
        self.assertIsNone(subq._result_cache)

        subq = Author.objects.filter(num__lt=3000)
        qs = Author.objects.exclude(pk__in=subq)
        self.assertSequenceEqual(qs, [self.a3, self.a4])

        # The subquery result cache should not be populated
        self.assertIsNone(subq._result_cache)

        subq = Author.objects.filter(num__lt=3000)
        self.assertSequenceEqual(
            Author.objects.filter(Q(pk__in=subq) & Q(name="a1")),
            [self.a1],
        )

        # The subquery result cache should not be populated
        self.assertIsNone(subq._result_cache)

    def test_ticket7076(self):
        # Excluding shouldn't eliminate NULL entries.
        self.assertSequenceEqual(
            Item.objects.exclude(modified=self.time1).order_by("name"),
            [self.i4, self.i3, self.i2],
        )
        self.assertSequenceEqual(
            Tag.objects.exclude(parent__name=self.t1.name),
            [self.t1, self.t4, self.t5],
        )

    def test_ticket7181(self):
        # Ordering by related tables should accommodate nullable fields (this
        # test is a little tricky, since NULL ordering is database dependent.
        # Instead, we just count the number of results).
        self.assertEqual(len(Tag.objects.order_by("parent__name")), 5)

        # Empty querysets can be merged with others.
        self.assertSequenceEqual(
            Note.objects.none() | Note.objects.all(),
            [self.n1, self.n2, self.n3],
        )
        self.assertSequenceEqual(
            Note.objects.all() | Note.objects.none(),
            [self.n1, self.n2, self.n3],
        )
        self.assertSequenceEqual(Note.objects.none() & Note.objects.all(), [])
        self.assertSequenceEqual(Note.objects.all() & Note.objects.none(), [])

    def test_ticket8439(self):
        # Complex combinations of conjunctions, disjunctions and nullable
        # relations.
        self.assertSequenceEqual(
            Author.objects.filter(
                Q(item__note__extrainfo=self.e2) | Q(report=self.r1, name="xyz")
            ),
            [self.a2],
        )
        self.assertSequenceEqual(
            Author.objects.filter(
                Q(report=self.r1, name="xyz") | Q(item__note__extrainfo=self.e2)
            ),
            [self.a2],
        )
        self.assertSequenceEqual(
            Annotation.objects.filter(
                Q(tag__parent=self.t1) | Q(notes__note="n1", name="a1")
            ),
            [self.ann1],
        )
        xx = ExtraInfo.objects.create(info="xx", note=self.n3)
        self.assertSequenceEqual(
            Note.objects.filter(Q(extrainfo__author=self.a1) | Q(extrainfo=xx)),
            [self.n1, self.n3],
        )
        q = Note.objects.filter(Q(extrainfo__author=self.a1) | Q(extrainfo=xx)).query
        self.assertEqual(
            len(
                [
                    x
                    for x in q.alias_map.values()
                    if x.join_type == LOUTER and q.alias_refcount[x.table_alias]
                ]
            ),
            1,
        )

    def test_ticket17429(self):
        """
        Meta.ordering=None works the same as Meta.ordering=[]
        """
        original_ordering = Tag._meta.ordering
        Tag._meta.ordering = None
        try:
            self.assertCountEqual(
                Tag.objects.all(),
                [self.t1, self.t2, self.t3, self.t4, self.t5],
            )
        finally:
            Tag._meta.ordering = original_ordering

    def test_exclude(self):
        self.assertQuerySetEqual(
            Item.objects.exclude(tags__name="t4"),
            Item.objects.filter(~Q(tags__name="t4")),
        )
        self.assertQuerySetEqual(
            Item.objects.exclude(Q(tags__name="t4") | Q(tags__name="t3")),
            Item.objects.filter(~(Q(tags__name="t4") | Q(tags__name="t3"))),
        )
        self.assertQuerySetEqual(
            Item.objects.exclude(Q(tags__name="t4") | ~Q(tags__name="t3")),
            Item.objects.filter(~(Q(tags__name="t4") | ~Q(tags__name="t3"))),
        )

    def test_nested_exclude(self):
        self.assertQuerySetEqual(
            Item.objects.exclude(~Q(tags__name="t4")),
            Item.objects.filter(~~Q(tags__name="t4")),
        )

    def test_double_exclude(self):
        self.assertQuerySetEqual(
            Item.objects.filter(Q(tags__name="t4")),
            Item.objects.filter(~~Q(tags__name="t4")),
        )
        self.assertQuerySetEqual(
            Item.objects.filter(Q(tags__name="t4")),
            Item.objects.filter(~Q(~Q(tags__name="t4"))),
        )

    def test_exclude_in(self):
        self.assertQuerySetEqual(
            Item.objects.exclude(Q(tags__name__in=["t4", "t3"])),
            Item.objects.filter(~Q(tags__name__in=["t4", "t3"])),
        )
        self.assertQuerySetEqual(
            Item.objects.filter(Q(tags__name__in=["t4", "t3"])),
            Item.objects.filter(~~Q(tags__name__in=["t4", "t3"])),
        )

    def test_ticket_10790_1(self):
        # Querying direct fields with isnull should trim the left outer join.
        # It also should not create INNER JOIN.
        q = Tag.objects.filter(parent__isnull=True)

        self.assertSequenceEqual(q, [self.t1])
        self.assertNotIn("JOIN", str(q.query))

        q = Tag.objects.filter(parent__isnull=False)

        self.assertSequenceEqual(q, [self.t2, self.t3, self.t4, self.t5])
        self.assertNotIn("JOIN", str(q.query))

        q = Tag.objects.exclude(parent__isnull=True)
        self.assertSequenceEqual(q, [self.t2, self.t3, self.t4, self.t5])
        self.assertNotIn("JOIN", str(q.query))

        q = Tag.objects.exclude(parent__isnull=False)
        self.assertSequenceEqual(q, [self.t1])
        self.assertNotIn("JOIN", str(q.query))

        q = Tag.objects.exclude(parent__parent__isnull=False)

        self.assertSequenceEqual(q, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 1)
        self.assertNotIn("INNER JOIN", str(q.query))

    def test_ticket_10790_2(self):
        # Querying across several tables should strip only the last outer join,
        # while preserving the preceding inner joins.
        q = Tag.objects.filter(parent__parent__isnull=False)

        self.assertSequenceEqual(q, [self.t4, self.t5])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 1)

        # Querying without isnull should not convert anything to left outer join.
        q = Tag.objects.filter(parent__parent=self.t1)
        self.assertSequenceEqual(q, [self.t4, self.t5])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 1)

    def test_ticket_10790_3(self):
        # Querying via indirect fields should populate the left outer join
        q = NamedCategory.objects.filter(tag__isnull=True)
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 1)
        # join to dumbcategory ptr_id
        self.assertEqual(str(q.query).count("INNER JOIN"), 1)
        self.assertSequenceEqual(q, [])

        # Querying across several tables should strip only the last join, while
        # preserving the preceding left outer joins.
        q = NamedCategory.objects.filter(tag__parent__isnull=True)
        self.assertEqual(str(q.query).count("INNER JOIN"), 1)
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 1)
        self.assertSequenceEqual(q, [self.nc1])

    def test_ticket_10790_4(self):
        # Querying across m2m field should not strip the m2m table from join.
        q = Author.objects.filter(item__tags__isnull=True)
        self.assertSequenceEqual(q, [self.a2, self.a3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 2)
        self.assertNotIn("INNER JOIN", str(q.query))

        q = Author.objects.filter(item__tags__parent__isnull=True)
        self.assertSequenceEqual(q, [self.a1, self.a2, self.a2, self.a3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 3)
        self.assertNotIn("INNER JOIN", str(q.query))

    def test_ticket_10790_5(self):
        # Querying with isnull=False across m2m field should not create outer joins
        q = Author.objects.filter(item__tags__isnull=False)
        self.assertSequenceEqual(q, [self.a1, self.a1, self.a2, self.a2, self.a4])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 2)

        q = Author.objects.filter(item__tags__parent__isnull=False)
        self.assertSequenceEqual(q, [self.a1, self.a2, self.a4])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 3)

        q = Author.objects.filter(item__tags__parent__parent__isnull=False)
        self.assertSequenceEqual(q, [self.a4])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 4)

    def test_ticket_10790_6(self):
        # Querying with isnull=True across m2m field should not create inner joins
        # and strip last outer join
        q = Author.objects.filter(item__tags__parent__parent__isnull=True)
        self.assertSequenceEqual(
            q,
            [self.a1, self.a1, self.a2, self.a2, self.a2, self.a3],
        )
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 4)
        self.assertEqual(str(q.query).count("INNER JOIN"), 0)

        q = Author.objects.filter(item__tags__parent__isnull=True)
        self.assertSequenceEqual(q, [self.a1, self.a2, self.a2, self.a3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 3)
        self.assertEqual(str(q.query).count("INNER JOIN"), 0)

    def test_ticket_10790_7(self):
        # Reverse querying with isnull should not strip the join
        q = Author.objects.filter(item__isnull=True)
        self.assertSequenceEqual(q, [self.a3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 1)
        self.assertEqual(str(q.query).count("INNER JOIN"), 0)

        q = Author.objects.filter(item__isnull=False)
        self.assertSequenceEqual(q, [self.a1, self.a2, self.a2, self.a4])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 1)

    def test_ticket_10790_8(self):
        # Querying with combined q-objects should also strip the left outer join
        q = Tag.objects.filter(Q(parent__isnull=True) | Q(parent=self.t1))
        self.assertSequenceEqual(q, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q.query).count("INNER JOIN"), 0)

    def test_ticket_10790_combine(self):
        # Combining queries should not re-populate the left outer join
        q1 = Tag.objects.filter(parent__isnull=True)
        q2 = Tag.objects.filter(parent__isnull=False)

        q3 = q1 | q2
        self.assertSequenceEqual(q3, [self.t1, self.t2, self.t3, self.t4, self.t5])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

        q3 = q1 & q2
        self.assertSequenceEqual(q3, [])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

        q2 = Tag.objects.filter(parent=self.t1)
        q3 = q1 | q2
        self.assertSequenceEqual(q3, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

        q3 = q2 | q1
        self.assertSequenceEqual(q3, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

        q1 = Tag.objects.filter(parent__isnull=True)
        q2 = Tag.objects.filter(parent__parent__isnull=True)

        q3 = q1 | q2
        self.assertSequenceEqual(q3, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 1)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

        q3 = q2 | q1
        self.assertSequenceEqual(q3, [self.t1, self.t2, self.t3])
        self.assertEqual(str(q3.query).count("LEFT OUTER JOIN"), 1)
        self.assertEqual(str(q3.query).count("INNER JOIN"), 0)

    def test_ticket19672(self):
        self.assertSequenceEqual(
            Report.objects.filter(
                Q(creator__isnull=False) & ~Q(creator__extra__value=41)
            ),
            [self.r1],
        )

    def test_ticket_20250(self):
        # A negated Q along with an annotated queryset failed in Django 1.4
        qs = Author.objects.annotate(Count("item"))
        qs = qs.filter(~Q(extra__value=0)).order_by("name")

        self.assertIn("SELECT", str(qs.query))
        self.assertSequenceEqual(qs, [self.a1, self.a2, self.a3, self.a4])

    def test_lookup_constraint_fielderror(self):
        msg = (
            "Cannot resolve keyword 'unknown_field' into field. Choices are: "
            "annotation, category, category_id, children, id, item, "
            "managedmodel, name, note, parent, parent_id"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Tag.objects.filter(unknown_field__name="generic")

    def test_common_mixed_case_foreign_keys(self):
        """
        Valid query should be generated when fields fetched from joined tables
        include FKs whose names only differ by case.
        """
        c1 = SimpleCategory.objects.create(name="c1")
        c2 = SimpleCategory.objects.create(name="c2")
        c3 = SimpleCategory.objects.create(name="c3")
        category = CategoryItem.objects.create(category=c1)
        mixed_case_field_category = MixedCaseFieldCategoryItem.objects.create(
            CaTeGoRy=c2
        )
        mixed_case_db_column_category = MixedCaseDbColumnCategoryItem.objects.create(
            category=c3
        )
        CommonMixedCaseForeignKeys.objects.create(
            category=category,
            mixed_case_field_category=mixed_case_field_category,
            mixed_case_db_column_category=mixed_case_db_column_category,
        )
        qs = CommonMixedCaseForeignKeys.objects.values(
            "category",
            "mixed_case_field_category",
            "mixed_case_db_column_category",
            "category__category",
            "mixed_case_field_category__CaTeGoRy",
            "mixed_case_db_column_category__category",
        )
        self.assertTrue(qs.first())

    def test_excluded_intermediary_m2m_table_joined(self):
        self.assertSequenceEqual(
            Note.objects.filter(~Q(tag__annotation__name=F("note"))),
            [self.n1, self.n2, self.n3],
        )
        self.assertSequenceEqual(
            Note.objects.filter(tag__annotation__name="a1").filter(
                ~Q(tag__annotation__name=F("note"))
            ),
            [],
        )

    def test_field_with_filterable(self):
        self.assertSequenceEqual(
            Author.objects.filter(extra=self.e2),
            [self.a3, self.a4],
        )

    def test_negate_field(self):
        self.assertSequenceEqual(
            Note.objects.filter(negate=True),
            [self.n1, self.n2],
        )
        self.assertSequenceEqual(Note.objects.exclude(negate=True), [self.n3])

    def test_combining_does_not_mutate(self):
        all_authors = Author.objects.all()
        authors_with_report = Author.objects.filter(
            Exists(Report.objects.filter(creator__pk=OuterRef("id")))
        )
        authors_without_report = all_authors.exclude(pk__in=authors_with_report)
        items_before = Item.objects.filter(creator__in=authors_without_report)
        self.assertCountEqual(items_before, [self.i2, self.i3, self.i4])
        # Combining querysets doesn't mutate them.
        all_authors | authors_with_report
        all_authors & authors_with_report

        authors_without_report = all_authors.exclude(pk__in=authors_with_report)
        items_after = Item.objects.filter(creator__in=authors_without_report)

        self.assertCountEqual(items_after, [self.i2, self.i3, self.i4])
        self.assertCountEqual(items_before, items_after)

    @skipUnlessDBFeature("supports_select_union")
    def test_union_values_subquery(self):
        items = Item.objects.filter(creator=OuterRef("pk"))
        item_authors = Author.objects.annotate(is_creator=Exists(items)).order_by()
        reports = Report.objects.filter(creator=OuterRef("pk"))
        report_authors = Author.objects.annotate(is_creator=Exists(reports)).order_by()
        all_authors = item_authors.union(report_authors).order_by("is_creator")
        self.assertEqual(
            list(all_authors.values_list("is_creator", flat=True)), [False, True]
        )


class Queries2Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.num4 = Number.objects.create(num=4)
        cls.num8 = Number.objects.create(num=8)
        cls.num12 = Number.objects.create(num=12)

    def test_ticket4289(self):
        # A slight variation on the restricting the filtering choices by the
        # lookup constraints.
        self.assertSequenceEqual(Number.objects.filter(num__lt=4), [])
        self.assertSequenceEqual(Number.objects.filter(num__gt=8, num__lt=12), [])
        self.assertSequenceEqual(
            Number.objects.filter(num__gt=8, num__lt=13),
            [self.num12],
        )
        self.assertSequenceEqual(
            Number.objects.filter(Q(num__lt=4) | Q(num__gt=8, num__lt=12)), []
        )
        self.assertSequenceEqual(
            Number.objects.filter(Q(num__gt=8, num__lt=12) | Q(num__lt=4)), []
        )
        self.assertSequenceEqual(
            Number.objects.filter(Q(num__gt=8) & Q(num__lt=12) | Q(num__lt=4)), []
        )
        self.assertSequenceEqual(
            Number.objects.filter(Q(num__gt=7) & Q(num__lt=12) | Q(num__lt=4)),
            [self.num8],
        )

    def test_ticket12239(self):
        # Custom lookups are registered to round float values correctly on gte
        # and lt IntegerField queries.
        self.assertSequenceEqual(
            Number.objects.filter(num__gt=11.9),
            [self.num12],
        )
        self.assertSequenceEqual(Number.objects.filter(num__gt=12), [])
        self.assertSequenceEqual(Number.objects.filter(num__gt=12.0), [])
        self.assertSequenceEqual(Number.objects.filter(num__gt=12.1), [])
        self.assertCountEqual(
            Number.objects.filter(num__lt=12),
            [self.num4, self.num8],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lt=12.0),
            [self.num4, self.num8],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lt=12.1),
            [self.num4, self.num8, self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__gte=11.9),
            [self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__gte=12),
            [self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__gte=12.0),
            [self.num12],
        )
        self.assertSequenceEqual(Number.objects.filter(num__gte=12.1), [])
        self.assertSequenceEqual(Number.objects.filter(num__gte=12.9), [])
        self.assertCountEqual(
            Number.objects.filter(num__lte=11.9),
            [self.num4, self.num8],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lte=12),
            [self.num4, self.num8, self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lte=12.0),
            [self.num4, self.num8, self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lte=12.1),
            [self.num4, self.num8, self.num12],
        )
        self.assertCountEqual(
            Number.objects.filter(num__lte=12.9),
            [self.num4, self.num8, self.num12],
        )

    def test_ticket7759(self):
        # Count should work with a partially read result set.
        count = Number.objects.count()
        qs = Number.objects.all()

        def run():
            for obj in qs:
                return qs.count() == count

        self.assertTrue(run())


class Queries3Tests(TestCase):
    def test_ticket7107(self):
        # This shouldn't create an infinite loop.
        self.assertSequenceEqual(Valid.objects.all(), [])

    def test_datetimes_invalid_field(self):
        # An error should be raised when QuerySet.datetimes() is passed the
        # wrong type of field.
        msg = "'name' isn't a DateField, TimeField, or DateTimeField."
        with self.assertRaisesMessage(TypeError, msg):
            Item.objects.datetimes("name", "month")

    def test_ticket22023(self):
        with self.assertRaisesMessage(
            TypeError, "Cannot call only() after .values() or .values_list()"
        ):
            Valid.objects.values().only()

        with self.assertRaisesMessage(
            TypeError, "Cannot call defer() after .values() or .values_list()"
        ):
            Valid.objects.values().defer()


class Queries4Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        generic = NamedCategory.objects.create(name="Generic")
        cls.t1 = Tag.objects.create(name="t1", category=generic)

        n1 = Note.objects.create(note="n1", misc="foo")
        n2 = Note.objects.create(note="n2", misc="bar")

        e1 = ExtraInfo.objects.create(info="e1", note=n1)
        e2 = ExtraInfo.objects.create(info="e2", note=n2)

        cls.a1 = Author.objects.create(name="a1", num=1001, extra=e1)
        cls.a3 = Author.objects.create(name="a3", num=3003, extra=e2)

        cls.r1 = Report.objects.create(name="r1", creator=cls.a1)
        cls.r2 = Report.objects.create(name="r2", creator=cls.a3)
        cls.r3 = Report.objects.create(name="r3")

        cls.i1 = Item.objects.create(
            name="i1", created=datetime.datetime.now(), note=n1, creator=cls.a1
        )
        cls.i2 = Item.objects.create(
            name="i2", created=datetime.datetime.now(), note=n1, creator=cls.a3
        )

    def test_ticket24525(self):
        tag = Tag.objects.create()
        anth100 = tag.note_set.create(note="ANTH", misc="100")
        math101 = tag.note_set.create(note="MATH", misc="101")
        s1 = tag.annotation_set.create(name="1")
        s2 = tag.annotation_set.create(name="2")
        s1.notes.set([math101, anth100])
        s2.notes.set([math101])
        result = math101.annotation_set.all() & tag.annotation_set.exclude(
            notes__in=[anth100]
        )
        self.assertEqual(list(result), [s2])

    def test_ticket11811(self):
        unsaved_category = NamedCategory(name="Other")
        msg = (
            "Unsaved model instance <NamedCategory: Other> cannot be used in an ORM "
            "query."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Tag.objects.filter(pk=self.t1.pk).update(category=unsaved_category)

    def test_ticket14876(self):
        # Note: when combining the query we need to have information available
        # about the join type of the trimmed "creator__isnull" join. If we
        # don't have that information, then the join is created as INNER JOIN
        # and results will be incorrect.
        q1 = Report.objects.filter(
            Q(creator__isnull=True) | Q(creator__extra__info="e1")
        )
        q2 = Report.objects.filter(Q(creator__isnull=True)) | Report.objects.filter(
            Q(creator__extra__info="e1")
        )
        self.assertCountEqual(q1, [self.r1, self.r3])
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Report.objects.filter(
            Q(creator__extra__info="e1") | Q(creator__isnull=True)
        )
        q2 = Report.objects.filter(
            Q(creator__extra__info="e1")
        ) | Report.objects.filter(Q(creator__isnull=True))
        self.assertCountEqual(q1, [self.r1, self.r3])
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Item.objects.filter(
            Q(creator=self.a1) | Q(creator__report__name="r1")
        ).order_by()
        q2 = (
            Item.objects.filter(Q(creator=self.a1)).order_by()
            | Item.objects.filter(Q(creator__report__name="r1")).order_by()
        )
        self.assertCountEqual(q1, [self.i1])
        self.assertEqual(str(q1.query), str(q2.query))

        q1 = Item.objects.filter(
            Q(creator__report__name="e1") | Q(creator=self.a1)
        ).order_by()
        q2 = (
            Item.objects.filter(Q(creator__report__name="e1")).order_by()
            | Item.objects.filter(Q(creator=self.a1)).order_by()
        )
        self.assertCountEqual(q1, [self.i1])
        self.assertEqual(str(q1.query), str(q2.query))

    def test_combine_join_reuse(self):
        # Joins having identical connections are correctly recreated in the
        # rhs query, in case the query is ORed together (#18748).
        Report.objects.create(name="r4", creator=self.a1)
        q1 = Author.objects.filter(report__name="r5")
        q2 = Author.objects.filter(report__name="r4").filter(report__name="r1")
        combined = q1 | q2
        self.assertEqual(str(combined.query).count("JOIN"), 2)
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0].name, "a1")

    def test_combine_or_filter_reuse(self):
        combined = Author.objects.filter(name="a1") | Author.objects.filter(name="a3")
        self.assertEqual(combined.get(name="a1"), self.a1)

    def test_join_reuse_order(self):
        # Join aliases are reused in order. This shouldn't raise AssertionError
        # because change_map contains a circular reference (#26522).
        s1 = School.objects.create()
        s2 = School.objects.create()
        s3 = School.objects.create()
        t1 = Teacher.objects.create()
        otherteachers = Teacher.objects.exclude(pk=t1.pk).exclude(friends=t1)
        qs1 = otherteachers.filter(schools=s1).filter(schools=s2)
        qs2 = otherteachers.filter(schools=s1).filter(schools=s3)
        self.assertSequenceEqual(qs1 | qs2, [])

    def test_ticket7095(self):
        # Updates that are filtered on the model being updated are somewhat
        # tricky in MySQL.
        ManagedModel.objects.create(data="mm1", tag=self.t1, public=True)
        self.assertEqual(ManagedModel.objects.update(data="mm"), 1)

        # A values() or values_list() query across joined models must use outer
        # joins appropriately.
        # Note: In Oracle, we expect a null CharField to return '' instead of
        # None.
        if connection.features.interprets_empty_strings_as_nulls:
            expected_null_charfield_repr = ""
        else:
            expected_null_charfield_repr = None
        self.assertSequenceEqual(
            Report.objects.values_list("creator__extra__info", flat=True).order_by(
                "name"
            ),
            ["e1", "e2", expected_null_charfield_repr],
        )

        # Similarly for select_related(), joins beyond an initial nullable join
        # must use outer joins so that all results are included.
        self.assertSequenceEqual(
            Report.objects.select_related("creator", "creator__extra").order_by("name"),
            [self.r1, self.r2, self.r3],
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
        self.assertEqual(obj.person.details.data, "d2")

    def test_order_by_resetting(self):
        # Calling order_by() with no parameters removes any existing ordering on the
        # model. But it should still be possible to add new ordering after that.
        qs = Author.objects.order_by().order_by("name")
        self.assertIn("ORDER BY", qs.query.get_compiler(qs.db).as_sql()[0])

    def test_order_by_reverse_fk(self):
        # It is possible to order by reverse of foreign key, although that can lead
        # to duplicate results.
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SimpleCategory.objects.create(name="category2")
        CategoryItem.objects.create(category=c1)
        CategoryItem.objects.create(category=c2)
        CategoryItem.objects.create(category=c1)
        self.assertSequenceEqual(
            SimpleCategory.objects.order_by("categoryitem", "pk"), [c1, c2, c1]
        )

    def test_filter_reverse_non_integer_pk(self):
        date_obj = DateTimePK.objects.create()
        extra_obj = ExtraInfo.objects.create(info="extra", date=date_obj)
        self.assertEqual(
            DateTimePK.objects.filter(extrainfo=extra_obj).get(),
            date_obj,
        )

    def test_ticket10181(self):
        # Avoid raising an EmptyResultSet if an inner query is probably
        # empty (and hence, not executed).
        self.assertSequenceEqual(
            Tag.objects.filter(id__in=Tag.objects.filter(id__in=[])), []
        )

    def test_ticket15316_filter_false(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(
            name="named category1", special_name="special1"
        )
        c3 = SpecialCategory.objects.create(
            name="named category2", special_name="special2"
        )

        CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.filter(category__specialcategory__isnull=False)
        self.assertEqual(qs.count(), 2)
        self.assertCountEqual(qs, [ci2, ci3])

    def test_ticket15316_exclude_false(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(
            name="named category1", special_name="special1"
        )
        c3 = SpecialCategory.objects.create(
            name="named category2", special_name="special2"
        )

        ci1 = CategoryItem.objects.create(category=c1)
        CategoryItem.objects.create(category=c2)
        CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.exclude(category__specialcategory__isnull=False)
        self.assertEqual(qs.count(), 1)
        self.assertSequenceEqual(qs, [ci1])

    def test_ticket15316_filter_true(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(
            name="named category1", special_name="special1"
        )
        c3 = SpecialCategory.objects.create(
            name="named category2", special_name="special2"
        )

        ci1 = CategoryItem.objects.create(category=c1)
        CategoryItem.objects.create(category=c2)
        CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.filter(category__specialcategory__isnull=True)
        self.assertEqual(qs.count(), 1)
        self.assertSequenceEqual(qs, [ci1])

    def test_ticket15316_exclude_true(self):
        c1 = SimpleCategory.objects.create(name="category1")
        c2 = SpecialCategory.objects.create(
            name="named category1", special_name="special1"
        )
        c3 = SpecialCategory.objects.create(
            name="named category2", special_name="special2"
        )

        CategoryItem.objects.create(category=c1)
        ci2 = CategoryItem.objects.create(category=c2)
        ci3 = CategoryItem.objects.create(category=c3)

        qs = CategoryItem.objects.exclude(category__specialcategory__isnull=True)
        self.assertEqual(qs.count(), 2)
        self.assertCountEqual(qs, [ci2, ci3])

    def test_ticket15316_one2one_filter_false(self):
        c = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        OneToOneCategory.objects.create(category=c1, new_name="new1")
        OneToOneCategory.objects.create(category=c0, new_name="new2")

        CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.filter(
            category__onetoonecategory__isnull=False
        ).order_by("pk")
        self.assertEqual(qs.count(), 2)
        self.assertSequenceEqual(qs, [ci2, ci3])

    def test_ticket15316_one2one_exclude_false(self):
        c = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        OneToOneCategory.objects.create(category=c1, new_name="new1")
        OneToOneCategory.objects.create(category=c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        CategoryItem.objects.create(category=c0)
        CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.exclude(category__onetoonecategory__isnull=False)
        self.assertEqual(qs.count(), 1)
        self.assertSequenceEqual(qs, [ci1])

    def test_ticket15316_one2one_filter_true(self):
        c = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        OneToOneCategory.objects.create(category=c1, new_name="new1")
        OneToOneCategory.objects.create(category=c0, new_name="new2")

        ci1 = CategoryItem.objects.create(category=c)
        CategoryItem.objects.create(category=c0)
        CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.filter(category__onetoonecategory__isnull=True)
        self.assertEqual(qs.count(), 1)
        self.assertSequenceEqual(qs, [ci1])

    def test_ticket15316_one2one_exclude_true(self):
        c = SimpleCategory.objects.create(name="cat")
        c0 = SimpleCategory.objects.create(name="cat0")
        c1 = SimpleCategory.objects.create(name="category1")

        OneToOneCategory.objects.create(category=c1, new_name="new1")
        OneToOneCategory.objects.create(category=c0, new_name="new2")

        CategoryItem.objects.create(category=c)
        ci2 = CategoryItem.objects.create(category=c0)
        ci3 = CategoryItem.objects.create(category=c1)

        qs = CategoryItem.objects.exclude(
            category__onetoonecategory__isnull=True
        ).order_by("pk")
        self.assertEqual(qs.count(), 2)
        self.assertSequenceEqual(qs, [ci2, ci3])


class Queries5Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Ordering by 'rank' gives us rank2, rank1, rank3. Ordering by the
        # Meta.ordering will be rank3, rank2, rank1.
        cls.n1 = Note.objects.create(note="n1", misc="foo", id=1)
        cls.n2 = Note.objects.create(note="n2", misc="bar", id=2)
        e1 = ExtraInfo.objects.create(info="e1", note=cls.n1)
        e2 = ExtraInfo.objects.create(info="e2", note=cls.n2)
        a1 = Author.objects.create(name="a1", num=1001, extra=e1)
        a2 = Author.objects.create(name="a2", num=2002, extra=e1)
        a3 = Author.objects.create(name="a3", num=3003, extra=e2)
        cls.rank2 = Ranking.objects.create(rank=2, author=a2)
        cls.rank1 = Ranking.objects.create(rank=1, author=a3)
        cls.rank3 = Ranking.objects.create(rank=3, author=a1)

    def test_ordering(self):
        # Cross model ordering is possible in Meta, too.
        self.assertSequenceEqual(
            Ranking.objects.all(),
            [self.rank3, self.rank2, self.rank1],
        )
        self.assertSequenceEqual(
            Ranking.objects.order_by("rank"),
            [self.rank1, self.rank2, self.rank3],
        )

        # Ordering of extra() pieces is possible, too and you can mix extra
        # fields and model fields in the ordering.
        self.assertSequenceEqual(
            Ranking.objects.extra(
                tables=["django_site"], order_by=["-django_site.id", "rank"]
            ),
            [self.rank1, self.rank2, self.rank3],
        )

        sql = "case when %s > 2 then 1 else 0 end" % connection.ops.quote_name("rank")
        qs = Ranking.objects.extra(select={"good": sql})
        self.assertEqual(
            [o.good for o in qs.extra(order_by=("-good",))], [True, False, False]
        )
        self.assertSequenceEqual(
            qs.extra(order_by=("-good", "id")),
            [self.rank3, self.rank2, self.rank1],
        )

        # Despite having some extra aliases in the query, we can still omit
        # them in a values() query.
        dicts = qs.values("id", "rank").order_by("id")
        self.assertEqual([d["rank"] for d in dicts], [2, 1, 3])

    def test_ticket7256(self):
        # An empty values() call includes all aliases, including those from an
        # extra()
        sql = "case when %s > 2 then 1 else 0 end" % connection.ops.quote_name("rank")
        qs = Ranking.objects.extra(select={"good": sql})
        dicts = qs.values().order_by("id")
        for d in dicts:
            del d["id"]
            del d["author_id"]
        self.assertEqual(
            [sorted(d.items()) for d in dicts],
            [
                [("good", 0), ("rank", 2)],
                [("good", 0), ("rank", 1)],
                [("good", 1), ("rank", 3)],
            ],
        )

    def test_ticket7045(self):
        # Extra tables used to crash SQL construction on the second use.
        qs = Ranking.objects.extra(tables=["django_site"])
        qs.query.get_compiler(qs.db).as_sql()
        # test passes if this doesn't raise an exception.
        qs.query.get_compiler(qs.db).as_sql()

    def test_ticket9848(self):
        # Make sure that updates which only filter on sub-tables don't
        # inadvertently update the wrong records (bug #9848).
        author_start = Author.objects.get(name="a1")
        ranking_start = Ranking.objects.get(author__name="a1")

        # Make sure that the IDs from different tables don't happen to match.
        self.assertSequenceEqual(
            Ranking.objects.filter(author__name="a1"),
            [self.rank3],
        )
        self.assertEqual(Ranking.objects.filter(author__name="a1").update(rank=4636), 1)

        r = Ranking.objects.get(author__name="a1")
        self.assertEqual(r.id, ranking_start.id)
        self.assertEqual(r.author.id, author_start.id)
        self.assertEqual(r.rank, 4636)
        r.rank = 3
        r.save()
        self.assertSequenceEqual(
            Ranking.objects.all(),
            [self.rank3, self.rank2, self.rank1],
        )

    def test_ticket5261(self):
        # Test different empty excludes.
        self.assertSequenceEqual(
            Note.objects.exclude(Q()),
            [self.n1, self.n2],
        )
        self.assertSequenceEqual(
            Note.objects.filter(~Q()),
            [self.n1, self.n2],
        )
        self.assertSequenceEqual(
            Note.objects.filter(~Q() | ~Q()),
            [self.n1, self.n2],
        )
        self.assertSequenceEqual(
            Note.objects.exclude(~Q() & ~Q()),
            [self.n1, self.n2],
        )
        self.assertSequenceEqual(
            Note.objects.exclude(~Q() ^ ~Q()),
            [self.n1, self.n2],
        )

    def test_extra_select_literal_percent_s(self):
        # Allow %%s to escape select clauses
        self.assertEqual(Note.objects.extra(select={"foo": "'%%s'"})[0].foo, "%s")
        self.assertEqual(
            Note.objects.extra(select={"foo": "'%%s bar %%s'"})[0].foo, "%s bar %s"
        )
        self.assertEqual(
            Note.objects.extra(select={"foo": "'bar %%s'"})[0].foo, "bar %s"
        )

    def test_extra_select_alias_sql_injection(self):
        crafted_alias = """injected_name" from "queries_note"; --"""
        msg = (
            "Column aliases cannot contain whitespace characters, quotation marks, "
            "semicolons, or SQL comments."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Note.objects.extra(select={crafted_alias: "1"})

    def test_queryset_reuse(self):
        # Using querysets doesn't mutate aliases.
        authors = Author.objects.filter(Q(name="a1") | Q(name="nonexistent"))
        self.assertEqual(Ranking.objects.filter(author__in=authors).get(), self.rank3)
        self.assertEqual(authors.count(), 1)

    def test_filter_unsaved_object(self):
        msg = "Model instances passed to related filters must be saved."
        company = Company.objects.create(name="Django")
        with self.assertRaisesMessage(ValueError, msg):
            Employment.objects.filter(employer=Company(name="unsaved"))
        with self.assertRaisesMessage(ValueError, msg):
            Employment.objects.filter(employer__in=[company, Company(name="unsaved")])
        with self.assertRaisesMessage(ValueError, msg):
            StaffUser.objects.filter(staff=Staff(name="unsaved"))


class SelectRelatedTests(TestCase):
    def test_tickets_3045_3288(self):
        # Once upon a time, select_related() with circular relations would loop
        # infinitely if you forgot to specify "depth". Now we set an arbitrary
        # default upper bound.
        self.assertSequenceEqual(X.objects.all(), [])
        self.assertSequenceEqual(X.objects.select_related(), [])


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
        self.assertQuerySetEqual(Related.objects.order_by("custom"), [])


class NullableRelOrderingTests(TestCase):
    def test_ticket10028(self):
        # Ordering by model related to nullable relations(!) should use outer
        # joins, so that all results are included.
        p1 = Plaything.objects.create(name="p1")
        self.assertSequenceEqual(Plaything.objects.all(), [p1])

    def test_join_already_in_query(self):
        # Ordering by model related to nullable relations should not change
        # the join type of already existing joins.
        Plaything.objects.create(name="p1")
        s = SingleObject.objects.create(name="s")
        r = RelatedObject.objects.create(single=s, f=1)
        p2 = Plaything.objects.create(name="p2", others=r)
        qs = Plaything.objects.filter(others__isnull=False).order_by("pk")
        self.assertNotIn("JOIN", str(qs.query))
        qs = Plaything.objects.filter(others__f__isnull=False).order_by("pk")
        self.assertIn("INNER", str(qs.query))
        qs = qs.order_by("others__single__name")
        # The ordering by others__single__pk will add one new join (to single)
        # and that join must be LEFT join. The already existing join to related
        # objects must be kept INNER. So, we have both an INNER and a LEFT join
        # in the query.
        self.assertEqual(str(qs.query).count("LEFT"), 1)
        self.assertEqual(str(qs.query).count("INNER"), 1)
        self.assertSequenceEqual(qs, [p2])


class DisjunctiveFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.n1 = Note.objects.create(note="n1", misc="foo", id=1)
        cls.e1 = ExtraInfo.objects.create(info="e1", note=cls.n1)

    def test_ticket7872(self):
        # Another variation on the disjunctive filtering theme.

        # For the purposes of this regression test, it's important that there is no
        # Join object related to the LeafA we create.
        l1 = LeafA.objects.create(data="first")
        self.assertSequenceEqual(LeafA.objects.all(), [l1])
        self.assertSequenceEqual(
            LeafA.objects.filter(Q(data="first") | Q(join__b__data="second")),
            [l1],
        )

    def test_ticket8283(self):
        # Checking that applying filters after a disjunction works correctly.
        self.assertSequenceEqual(
            (
                ExtraInfo.objects.filter(note=self.n1)
                | ExtraInfo.objects.filter(info="e2")
            ).filter(note=self.n1),
            [self.e1],
        )
        self.assertSequenceEqual(
            (
                ExtraInfo.objects.filter(info="e2")
                | ExtraInfo.objects.filter(note=self.n1)
            ).filter(note=self.n1),
            [self.e1],
        )


class Queries6Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        generic = NamedCategory.objects.create(name="Generic")
        cls.t1 = Tag.objects.create(name="t1", category=generic)
        cls.t2 = Tag.objects.create(name="t2", parent=cls.t1, category=generic)
        cls.t3 = Tag.objects.create(name="t3", parent=cls.t1)
        cls.t4 = Tag.objects.create(name="t4", parent=cls.t3)
        cls.t5 = Tag.objects.create(name="t5", parent=cls.t3)
        n1 = Note.objects.create(note="n1", misc="foo", id=1)
        cls.ann1 = Annotation.objects.create(name="a1", tag=cls.t1)
        cls.ann1.notes.add(n1)
        cls.ann2 = Annotation.objects.create(name="a2", tag=cls.t4)

    def test_parallel_iterators(self):
        # Parallel iterators work.
        qs = Tag.objects.all()
        i1, i2 = iter(qs), iter(qs)
        self.assertEqual(repr(next(i1)), "<Tag: t1>")
        self.assertEqual(repr(next(i1)), "<Tag: t2>")
        self.assertEqual(repr(next(i2)), "<Tag: t1>")
        self.assertEqual(repr(next(i2)), "<Tag: t2>")
        self.assertEqual(repr(next(i2)), "<Tag: t3>")
        self.assertEqual(repr(next(i1)), "<Tag: t3>")

        qs = X.objects.all()
        self.assertFalse(qs)
        self.assertFalse(qs)

    def test_nested_queries_sql(self):
        # Nested queries should not evaluate the inner query as part of constructing the
        # SQL (so we should see a nested query here, indicated by two "SELECT" calls).
        qs = Annotation.objects.filter(notes__in=Note.objects.filter(note="xyzzy"))
        self.assertEqual(qs.query.get_compiler(qs.db).as_sql()[0].count("SELECT"), 2)

    def test_tickets_8921_9188(self):
        # Incorrect SQL was being generated for certain types of exclude()
        # queries that crossed multi-valued relations (#8921, #9188 and some
        # preemptively discovered cases).

        self.assertSequenceEqual(
            PointerA.objects.filter(connection__pointerb__id=1), []
        )
        self.assertSequenceEqual(
            PointerA.objects.exclude(connection__pointerb__id=1), []
        )

        self.assertSequenceEqual(
            Tag.objects.exclude(children=None),
            [self.t1, self.t3],
        )

        # This example is tricky because the parent could be NULL, so only checking
        # parents with annotations omits some results (tag t1, in this case).
        self.assertSequenceEqual(
            Tag.objects.exclude(parent__annotation__name="a1"),
            [self.t1, self.t4, self.t5],
        )

        # The annotation->tag link is single values and tag->children links is
        # multi-valued. So we have to split the exclude filter in the middle
        # and then optimize the inner query without losing results.
        self.assertSequenceEqual(
            Annotation.objects.exclude(tag__children__name="t2"),
            [self.ann2],
        )

        # Nested queries are possible (although should be used with care, since
        # they have performance problems on backends like MySQL.
        self.assertSequenceEqual(
            Annotation.objects.filter(notes__in=Note.objects.filter(note="n1")),
            [self.ann1],
        )

    def test_ticket3739(self):
        # The all() method on querysets returns a copy of the queryset.
        q1 = Tag.objects.order_by("name")
        self.assertIsNot(q1, q1.all())

    def test_ticket_11320(self):
        qs = Tag.objects.exclude(category=None).exclude(category__name="foo")
        self.assertEqual(str(qs.query).count(" INNER JOIN "), 1)

    def test_distinct_ordered_sliced_subquery_aggregation(self):
        self.assertEqual(
            Tag.objects.distinct().order_by("category__name")[:3].count(), 3
        )

    def test_multiple_columns_with_the_same_name_slice(self):
        self.assertEqual(
            list(
                Tag.objects.order_by("name").values_list("name", "category__name")[:2]
            ),
            [("t1", "Generic"), ("t2", "Generic")],
        )
        self.assertSequenceEqual(
            Tag.objects.order_by("name").select_related("category")[:2],
            [self.t1, self.t2],
        )
        self.assertEqual(
            list(Tag.objects.order_by("-name").values_list("name", "parent__name")[:2]),
            [("t5", "t3"), ("t4", "t3")],
        )
        self.assertSequenceEqual(
            Tag.objects.order_by("-name").select_related("parent")[:2],
            [self.t5, self.t4],
        )

    def test_col_alias_quoted(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.assertEqual(
                Tag.objects.values("parent")
                .annotate(
                    tag_per_parent=Count("pk"),
                )
                .aggregate(Max("tag_per_parent")),
                {"tag_per_parent__max": 2},
            )
        sql = captured_queries[0]["sql"]
        self.assertIn("AS %s" % connection.ops.quote_name("parent"), sql)

    def test_xor_subquery(self):
        self.assertSequenceEqual(
            Tag.objects.filter(
                Exists(Tag.objects.filter(id=OuterRef("id"), name="t3"))
                ^ Exists(Tag.objects.filter(id=OuterRef("id"), parent=self.t1))
            ),
            [self.t2],
        )


class RawQueriesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Note.objects.create(note="n1", misc="foo", id=1)

    def test_ticket14729(self):
        # Test representation of raw query with one or few parameters passed as list
        query = "SELECT * FROM queries_note WHERE note = %s"
        params = ["n1"]
        qs = Note.objects.raw(query, params=params)
        self.assertEqual(
            repr(qs), "<RawQuerySet: SELECT * FROM queries_note WHERE note = n1>"
        )

        query = "SELECT * FROM queries_note WHERE note = %s and misc = %s"
        params = ["n1", "foo"]
        qs = Note.objects.raw(query, params=params)
        self.assertEqual(
            repr(qs),
            "<RawQuerySet: SELECT * FROM queries_note WHERE note = n1 and misc = foo>",
        )


class GeneratorExpressionTests(SimpleTestCase):
    def test_ticket10432(self):
        # Using an empty iterator as the rvalue for an "__in"
        # lookup is legal.
        self.assertCountEqual(Note.objects.filter(pk__in=iter(())), [])


class ComparisonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.n1 = Note.objects.create(note="n1", misc="foo", id=1)
        e1 = ExtraInfo.objects.create(info="e1", note=cls.n1)
        cls.a2 = Author.objects.create(name="a2", num=2002, extra=e1)

    def test_ticket8597(self):
        # Regression tests for case-insensitive comparisons
        item_ab = Item.objects.create(
            name="a_b", created=datetime.datetime.now(), creator=self.a2, note=self.n1
        )
        item_xy = Item.objects.create(
            name="x%y", created=datetime.datetime.now(), creator=self.a2, note=self.n1
        )
        self.assertSequenceEqual(
            Item.objects.filter(name__iexact="A_b"),
            [item_ab],
        )
        self.assertSequenceEqual(
            Item.objects.filter(name__iexact="x%Y"),
            [item_xy],
        )
        self.assertSequenceEqual(
            Item.objects.filter(name__istartswith="A_b"),
            [item_ab],
        )
        self.assertSequenceEqual(
            Item.objects.filter(name__iendswith="A_b"),
            [item_ab],
        )


class ExistsSql(TestCase):
    def test_exists(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.assertFalse(Tag.objects.exists())
        # Ok - so the exist query worked - but did it include too many columns?
        self.assertEqual(len(captured_queries), 1)
        qstr = captured_queries[0]["sql"]
        id, name = connection.ops.quote_name("id"), connection.ops.quote_name("name")
        self.assertNotIn(id, qstr)
        self.assertNotIn(name, qstr)

    def test_distinct_exists(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.assertIs(Article.objects.distinct().exists(), False)
        self.assertEqual(len(captured_queries), 1)
        captured_sql = captured_queries[0]["sql"]
        self.assertNotIn(connection.ops.quote_name("id"), captured_sql)
        self.assertNotIn(connection.ops.quote_name("name"), captured_sql)

    def test_sliced_distinct_exists(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.assertIs(Article.objects.distinct()[1:3].exists(), False)
        self.assertEqual(len(captured_queries), 1)
        captured_sql = captured_queries[0]["sql"]
        self.assertIn(connection.ops.quote_name("id"), captured_sql)
        self.assertIn(connection.ops.quote_name("name"), captured_sql)

    def test_ticket_18414(self):
        Article.objects.create(name="one", created=datetime.datetime.now())
        Article.objects.create(name="one", created=datetime.datetime.now())
        Article.objects.create(name="two", created=datetime.datetime.now())
        self.assertTrue(Article.objects.exists())
        self.assertTrue(Article.objects.distinct().exists())
        self.assertTrue(Article.objects.distinct()[1:3].exists())
        self.assertFalse(Article.objects.distinct()[1:1].exists())

    @skipUnlessDBFeature("can_distinct_on_fields")
    def test_ticket_18414_distinct_on(self):
        Article.objects.create(name="one", created=datetime.datetime.now())
        Article.objects.create(name="one", created=datetime.datetime.now())
        Article.objects.create(name="two", created=datetime.datetime.now())
        self.assertTrue(Article.objects.distinct("name").exists())
        self.assertTrue(Article.objects.distinct("name")[1:2].exists())
        self.assertFalse(Article.objects.distinct("name")[2:3].exists())


class QuerysetOrderedTests(unittest.TestCase):
    """
    Tests for the Queryset.ordered attribute.
    """

    def test_no_default_or_explicit_ordering(self):
        self.assertIs(Annotation.objects.all().ordered, False)

    def test_cleared_default_ordering(self):
        self.assertIs(Tag.objects.all().ordered, True)
        self.assertIs(Tag.objects.order_by().ordered, False)

    def test_explicit_ordering(self):
        self.assertIs(Annotation.objects.order_by("id").ordered, True)

    def test_empty_queryset(self):
        self.assertIs(Annotation.objects.none().ordered, True)

    def test_order_by_extra(self):
        self.assertIs(Annotation.objects.extra(order_by=["id"]).ordered, True)

    def test_annotated_ordering(self):
        qs = Annotation.objects.annotate(num_notes=Count("notes"))
        self.assertIs(qs.ordered, False)
        self.assertIs(qs.order_by("num_notes").ordered, True)

    def test_annotated_default_ordering(self):
        qs = Tag.objects.annotate(num_notes=Count("pk"))
        self.assertIs(qs.ordered, False)
        self.assertIs(qs.order_by("name").ordered, True)

    def test_annotated_values_default_ordering(self):
        qs = Tag.objects.values("name").annotate(num_notes=Count("pk"))
        self.assertIs(qs.ordered, False)
        self.assertIs(qs.order_by("name").ordered, True)


@skipUnlessDBFeature("allow_sliced_subqueries_with_in")
class SubqueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        NamedCategory.objects.create(id=1, name="first")
        NamedCategory.objects.create(id=2, name="second")
        NamedCategory.objects.create(id=3, name="third")
        NamedCategory.objects.create(id=4, name="fourth")

    def test_ordered_subselect(self):
        "Subselects honor any manual ordering"
        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[0:2]
        )
        self.assertEqual(set(query.values_list("id", flat=True)), {3, 4})

        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[:2]
        )
        self.assertEqual(set(query.values_list("id", flat=True)), {3, 4})

        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[1:2]
        )
        self.assertEqual(set(query.values_list("id", flat=True)), {3})

        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[2:]
        )
        self.assertEqual(set(query.values_list("id", flat=True)), {1, 2})

    def test_slice_subquery_and_query(self):
        """
        Slice a query that has a sliced subquery
        """
        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[0:2]
        ).order_by("id")[0:2]
        self.assertSequenceEqual([x.id for x in query], [3, 4])

        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[1:3]
        ).order_by("id")[1:3]
        self.assertSequenceEqual([x.id for x in query], [3])

        query = DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[2:]
        ).order_by("id")[1:]
        self.assertSequenceEqual([x.id for x in query], [2])

    def test_related_sliced_subquery(self):
        """
        Related objects constraints can safely contain sliced subqueries.
        refs #22434
        """
        generic = NamedCategory.objects.create(id=5, name="Generic")
        t1 = Tag.objects.create(name="t1", category=generic)
        t2 = Tag.objects.create(name="t2", category=generic)
        ManagedModel.objects.create(data="mm1", tag=t1, public=True)
        mm2 = ManagedModel.objects.create(data="mm2", tag=t2, public=True)

        query = ManagedModel.normal_manager.filter(
            tag__in=Tag.objects.order_by("-id")[:1]
        )
        self.assertEqual({x.id for x in query}, {mm2.id})

    def test_sliced_delete(self):
        "Delete queries can safely contain sliced subqueries"
        DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[0:1]
        ).delete()
        self.assertEqual(
            set(DumbCategory.objects.values_list("id", flat=True)), {1, 2, 3}
        )

        DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[1:2]
        ).delete()
        self.assertEqual(set(DumbCategory.objects.values_list("id", flat=True)), {1, 3})

        DumbCategory.objects.filter(
            id__in=DumbCategory.objects.order_by("-id")[1:]
        ).delete()
        self.assertEqual(set(DumbCategory.objects.values_list("id", flat=True)), {3})

    def test_distinct_ordered_sliced_subquery(self):
        # Implicit values('id').
        self.assertSequenceEqual(
            NamedCategory.objects.filter(
                id__in=NamedCategory.objects.distinct().order_by("name")[0:2],
            )
            .order_by("name")
            .values_list("name", flat=True),
            ["first", "fourth"],
        )
        # Explicit values('id').
        self.assertSequenceEqual(
            NamedCategory.objects.filter(
                id__in=NamedCategory.objects.distinct()
                .order_by("-name")
                .values("id")[0:2],
            )
            .order_by("name")
            .values_list("name", flat=True),
            ["second", "third"],
        )
        # Annotated value.
        self.assertSequenceEqual(
            DumbCategory.objects.filter(
                id__in=DumbCategory.objects.annotate(double_id=F("id") * 2)
                .order_by("id")
                .distinct()
                .values("double_id")[0:2],
            )
            .order_by("id")
            .values_list("id", flat=True),
            [2, 4],
        )


class QuerySetBitwiseOperationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create()
        cls.room_1 = Classroom.objects.create(
            school=cls.school, has_blackboard=False, name="Room 1"
        )
        cls.room_2 = Classroom.objects.create(
            school=cls.school, has_blackboard=True, name="Room 2"
        )
        cls.room_3 = Classroom.objects.create(
            school=cls.school, has_blackboard=True, name="Room 3"
        )
        cls.room_4 = Classroom.objects.create(
            school=cls.school, has_blackboard=False, name="Room 4"
        )
        tag = Tag.objects.create()
        cls.annotation_1 = Annotation.objects.create(tag=tag)
        annotation_2 = Annotation.objects.create(tag=tag)
        note = cls.annotation_1.notes.create(tag=tag)
        cls.base_user_1 = BaseUser.objects.create(annotation=cls.annotation_1)
        cls.base_user_2 = BaseUser.objects.create(annotation=annotation_2)
        cls.task = Task.objects.create(
            owner=cls.base_user_2,
            creator=cls.base_user_2,
            note=note,
        )

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_or_with_rhs_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=True)
        qs2 = Classroom.objects.filter(has_blackboard=False)[:1]
        self.assertCountEqual(qs1 | qs2, [self.room_1, self.room_2, self.room_3])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_or_with_lhs_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=True)[:1]
        qs2 = Classroom.objects.filter(has_blackboard=False)
        self.assertCountEqual(qs1 | qs2, [self.room_1, self.room_2, self.room_4])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_or_with_both_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=False)[:1]
        qs2 = Classroom.objects.filter(has_blackboard=True)[:1]
        self.assertCountEqual(qs1 | qs2, [self.room_1, self.room_2])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_or_with_both_slice_and_ordering(self):
        qs1 = Classroom.objects.filter(has_blackboard=False).order_by("-pk")[:1]
        qs2 = Classroom.objects.filter(has_blackboard=True).order_by("-name")[:1]
        self.assertCountEqual(qs1 | qs2, [self.room_3, self.room_4])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_xor_with_rhs_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=True)
        qs2 = Classroom.objects.filter(has_blackboard=False)[:1]
        self.assertCountEqual(qs1 ^ qs2, [self.room_1, self.room_2, self.room_3])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_xor_with_lhs_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=True)[:1]
        qs2 = Classroom.objects.filter(has_blackboard=False)
        self.assertCountEqual(qs1 ^ qs2, [self.room_1, self.room_2, self.room_4])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_xor_with_both_slice(self):
        qs1 = Classroom.objects.filter(has_blackboard=False)[:1]
        qs2 = Classroom.objects.filter(has_blackboard=True)[:1]
        self.assertCountEqual(qs1 ^ qs2, [self.room_1, self.room_2])

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_xor_with_both_slice_and_ordering(self):
        qs1 = Classroom.objects.filter(has_blackboard=False).order_by("-pk")[:1]
        qs2 = Classroom.objects.filter(has_blackboard=True).order_by("-name")[:1]
        self.assertCountEqual(qs1 ^ qs2, [self.room_3, self.room_4])

    def test_subquery_aliases(self):
        combined = School.objects.filter(pk__isnull=False) & School.objects.filter(
            Exists(
                Classroom.objects.filter(
                    has_blackboard=True,
                    school=OuterRef("pk"),
                )
            ),
        )
        self.assertSequenceEqual(combined, [self.school])
        nested_combined = School.objects.filter(pk__in=combined.values("pk"))
        self.assertSequenceEqual(nested_combined, [self.school])

    def test_conflicting_aliases_during_combine(self):
        qs1 = self.annotation_1.baseuser_set.all()
        qs2 = BaseUser.objects.filter(
            Q(owner__note__in=self.annotation_1.notes.all())
            | Q(creator__note__in=self.annotation_1.notes.all())
        )
        self.assertSequenceEqual(qs1, [self.base_user_1])
        self.assertSequenceEqual(qs2, [self.base_user_2])
        self.assertCountEqual(qs2 | qs1, qs1 | qs2)
        self.assertCountEqual(qs2 | qs1, [self.base_user_1, self.base_user_2])


class CloneTests(TestCase):
    def test_evaluated_queryset_as_argument(self):
        """
        If a queryset is already evaluated, it can still be used as a query arg.
        """
        n = Note(note="Test1", misc="misc")
        n.save()
        e = ExtraInfo(info="good", note=n)
        e.save()

        n_list = Note.objects.all()
        # Evaluate the Note queryset, populating the query cache
        list(n_list)
        # Make one of cached results unpickable.
        n_list._result_cache[0].error = UnpickleableError()
        with self.assertRaises(UnpickleableError):
            pickle.dumps(n_list)
        # Use the note queryset in a query, and evaluate
        # that query in a way that involves cloning.
        self.assertEqual(ExtraInfo.objects.filter(note__in=n_list)[0].info, "good")

    def test_no_model_options_cloning(self):
        """
        Cloning a queryset does not get out of hand. While complete
        testing is impossible, this is a sanity check against invalid use of
        deepcopy. refs #16759.
        """
        opts_class = type(Note._meta)
        note_deepcopy = getattr(opts_class, "__deepcopy__", None)
        opts_class.__deepcopy__ = lambda obj, memo: self.fail(
            "Model options shouldn't be cloned."
        )
        try:
            Note.objects.filter(pk__lte=F("pk") + 1).all()
        finally:
            if note_deepcopy is None:
                delattr(opts_class, "__deepcopy__")
            else:
                opts_class.__deepcopy__ = note_deepcopy

    def test_no_fields_cloning(self):
        """
        Cloning a queryset does not get out of hand. While complete
        testing is impossible, this is a sanity check against invalid use of
        deepcopy. refs #16759.
        """
        opts_class = type(Note._meta.get_field("misc"))
        note_deepcopy = getattr(opts_class, "__deepcopy__", None)
        opts_class.__deepcopy__ = lambda obj, memo: self.fail(
            "Model fields shouldn't be cloned"
        )
        try:
            Note.objects.filter(note=F("misc")).all()
        finally:
            if note_deepcopy is None:
                delattr(opts_class, "__deepcopy__")
            else:
                opts_class.__deepcopy__ = note_deepcopy


class EmptyQuerySetTests(SimpleTestCase):
    def test_emptyqueryset_values(self):
        # #14366 -- Calling .values() on an empty QuerySet and then cloning
        # that should not cause an error
        self.assertCountEqual(Number.objects.none().values("num").order_by("num"), [])

    def test_values_subquery(self):
        self.assertCountEqual(
            Number.objects.filter(pk__in=Number.objects.none().values("pk")), []
        )
        self.assertCountEqual(
            Number.objects.filter(pk__in=Number.objects.none().values_list("pk")), []
        )

    def test_ticket_19151(self):
        # #19151 -- Calling .values() or .values_list() on an empty QuerySet
        # should return an empty QuerySet and not cause an error.
        q = Author.objects.none()
        self.assertCountEqual(q.values(), [])
        self.assertCountEqual(q.values_list(), [])


class ValuesQuerysetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Number.objects.create(num=72)

    def test_flat_values_list(self):
        qs = Number.objects.values_list("num")
        qs = qs.values_list("num", flat=True)
        self.assertSequenceEqual(qs, [72])

    def test_extra_values(self):
        # testing for ticket 14930 issues
        qs = Number.objects.extra(
            select={"value_plus_x": "num+%s", "value_minus_x": "num-%s"},
            select_params=(1, 2),
        )
        qs = qs.order_by("value_minus_x")
        qs = qs.values("num")
        self.assertSequenceEqual(qs, [{"num": 72}])

    def test_extra_values_order_twice(self):
        # testing for ticket 14930 issues
        qs = Number.objects.extra(
            select={"value_plus_one": "num+1", "value_minus_one": "num-1"}
        )
        qs = qs.order_by("value_minus_one").order_by("value_plus_one")
        qs = qs.values("num")
        self.assertSequenceEqual(qs, [{"num": 72}])

    def test_extra_values_order_multiple(self):
        # Postgres doesn't allow constants in order by, so check for that.
        qs = Number.objects.extra(
            select={
                "value_plus_one": "num+1",
                "value_minus_one": "num-1",
                "constant_value": "1",
            }
        )
        qs = qs.order_by("value_plus_one", "value_minus_one", "constant_value")
        qs = qs.values("num")
        self.assertSequenceEqual(qs, [{"num": 72}])

    def test_extra_values_order_in_extra(self):
        # testing for ticket 14930 issues
        qs = Number.objects.extra(
            select={"value_plus_one": "num+1", "value_minus_one": "num-1"},
            order_by=["value_minus_one"],
        )
        qs = qs.values("num")

    def test_extra_select_params_values_order_in_extra(self):
        # testing for 23259 issue
        qs = Number.objects.extra(
            select={"value_plus_x": "num+%s"},
            select_params=[1],
            order_by=["value_plus_x"],
        )
        qs = qs.filter(num=72)
        qs = qs.values("num")
        self.assertSequenceEqual(qs, [{"num": 72}])

    def test_extra_multiple_select_params_values_order_by(self):
        # testing for 23259 issue
        qs = Number.objects.extra(
            select={"value_plus_x": "num+%s", "value_minus_x": "num-%s"},
            select_params=(72, 72),
        )
        qs = qs.order_by("value_minus_x")
        qs = qs.filter(num=1)
        qs = qs.values("num")
        self.assertSequenceEqual(qs, [])

    def test_extra_values_list(self):
        # testing for ticket 14930 issues
        qs = Number.objects.extra(select={"value_plus_one": "num+1"})
        qs = qs.order_by("value_plus_one")
        qs = qs.values_list("num")
        self.assertSequenceEqual(qs, [(72,)])

    def test_flat_extra_values_list(self):
        # testing for ticket 14930 issues
        qs = Number.objects.extra(select={"value_plus_one": "num+1"})
        qs = qs.order_by("value_plus_one")
        qs = qs.values_list("num", flat=True)
        self.assertSequenceEqual(qs, [72])

    def test_field_error_values_list(self):
        # see #23443
        msg = (
            "Cannot resolve keyword %r into field. Join on 'name' not permitted."
            % "foo"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Tag.objects.values_list("name__foo")

    def test_named_values_list_flat(self):
        msg = "'flat' and 'named' can't be used together."
        with self.assertRaisesMessage(TypeError, msg):
            Number.objects.values_list("num", flat=True, named=True)

    def test_named_values_list_bad_field_name(self):
        msg = "Type names and field names must be valid identifiers: '1'"
        with self.assertRaisesMessage(ValueError, msg):
            Number.objects.extra(select={"1": "num+1"}).values_list(
                "1", named=True
            ).first()

    def test_named_values_list_with_fields(self):
        qs = Number.objects.extra(select={"num2": "num+1"}).annotate(Count("id"))
        values = qs.values_list("num", "num2", named=True).first()
        self.assertEqual(type(values).__name__, "Row")
        self.assertEqual(values._fields, ("num", "num2"))
        self.assertEqual(values.num, 72)
        self.assertEqual(values.num2, 73)

    def test_named_values_list_without_fields(self):
        qs = Number.objects.extra(select={"num2": "num+1"}).annotate(Count("id"))
        values = qs.values_list(named=True).first()
        self.assertEqual(type(values).__name__, "Row")
        self.assertEqual(
            values._fields,
            ("num2", "id", "num", "other_num", "another_num", "id__count"),
        )
        self.assertEqual(values.num, 72)
        self.assertEqual(values.num2, 73)
        self.assertEqual(values.id__count, 1)

    def test_named_values_list_expression_with_default_alias(self):
        expr = Count("id")
        values = (
            Number.objects.annotate(id__count1=expr)
            .values_list(expr, "id__count1", named=True)
            .first()
        )
        self.assertEqual(values._fields, ("id__count2", "id__count1"))

    def test_named_values_list_expression(self):
        expr = F("num") + 1
        qs = Number.objects.annotate(combinedexpression1=expr).values_list(
            expr, "combinedexpression1", named=True
        )
        values = qs.first()
        self.assertEqual(values._fields, ("combinedexpression2", "combinedexpression1"))

    def test_named_values_pickle(self):
        value = Number.objects.values_list("num", "other_num", named=True).get()
        self.assertEqual(value, (72, None))
        self.assertEqual(pickle.loads(pickle.dumps(value)), value)


class QuerySetSupportsPythonIdioms(TestCase):
    @classmethod
    def setUpTestData(cls):
        some_date = datetime.datetime(2014, 5, 16, 12, 1)
        cls.articles = [
            Article.objects.create(name=f"Article {i}", created=some_date)
            for i in range(1, 8)
        ]

    def get_ordered_articles(self):
        return Article.objects.order_by("name")

    def test_can_get_items_using_index_and_slice_notation(self):
        self.assertEqual(self.get_ordered_articles()[0].name, "Article 1")
        self.assertSequenceEqual(
            self.get_ordered_articles()[1:3],
            [self.articles[1], self.articles[2]],
        )

    def test_slicing_with_steps_can_be_used(self):
        self.assertSequenceEqual(
            self.get_ordered_articles()[::2],
            [
                self.articles[0],
                self.articles[2],
                self.articles[4],
                self.articles[6],
            ],
        )

    def test_slicing_without_step_is_lazy(self):
        with self.assertNumQueries(0):
            self.get_ordered_articles()[0:5]

    def test_slicing_with_tests_is_not_lazy(self):
        with self.assertNumQueries(1):
            self.get_ordered_articles()[0:5:3]

    def test_slicing_can_slice_again_after_slicing(self):
        self.assertSequenceEqual(
            self.get_ordered_articles()[0:5][0:2],
            [self.articles[0], self.articles[1]],
        )
        self.assertSequenceEqual(
            self.get_ordered_articles()[0:5][4:], [self.articles[4]]
        )
        self.assertSequenceEqual(self.get_ordered_articles()[0:5][5:], [])

        # Some more tests!
        self.assertSequenceEqual(
            self.get_ordered_articles()[2:][0:2],
            [self.articles[2], self.articles[3]],
        )
        self.assertSequenceEqual(
            self.get_ordered_articles()[2:][:2],
            [self.articles[2], self.articles[3]],
        )
        self.assertSequenceEqual(
            self.get_ordered_articles()[2:][2:3], [self.articles[4]]
        )

        # Using an offset without a limit is also possible.
        self.assertSequenceEqual(
            self.get_ordered_articles()[5:],
            [self.articles[5], self.articles[6]],
        )

    def test_slicing_cannot_filter_queryset_once_sliced(self):
        msg = "Cannot filter a query once a slice has been taken."
        with self.assertRaisesMessage(TypeError, msg):
            Article.objects.all()[0:5].filter(id=1)

    def test_slicing_cannot_reorder_queryset_once_sliced(self):
        msg = "Cannot reorder a query once a slice has been taken."
        with self.assertRaisesMessage(TypeError, msg):
            Article.objects.all()[0:5].order_by("id")

    def test_slicing_cannot_combine_queries_once_sliced(self):
        msg = "Cannot combine queries once a slice has been taken."
        with self.assertRaisesMessage(TypeError, msg):
            Article.objects.all()[0:1] & Article.objects.all()[4:5]

    def test_slicing_negative_indexing_not_supported_for_single_element(self):
        """hint: inverting your ordering might do what you need"""
        msg = "Negative indexing is not supported."
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.all()[-1]

    def test_slicing_negative_indexing_not_supported_for_range(self):
        """hint: inverting your ordering might do what you need"""
        msg = "Negative indexing is not supported."
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.all()[0:-5]
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.all()[-1:]

    def test_invalid_index(self):
        msg = "QuerySet indices must be integers or slices, not str."
        with self.assertRaisesMessage(TypeError, msg):
            Article.objects.all()["foo"]

    def test_can_get_number_of_items_in_queryset_using_standard_len(self):
        self.assertEqual(len(Article.objects.filter(name__exact="Article 1")), 1)

    def test_can_combine_queries_using_and_and_or_operators(self):
        s1 = Article.objects.filter(name__exact="Article 1")
        s2 = Article.objects.filter(name__exact="Article 2")
        self.assertSequenceEqual(
            (s1 | s2).order_by("name"),
            [self.articles[0], self.articles[1]],
        )
        self.assertSequenceEqual(s1 & s2, [])


class WeirdQuerysetSlicingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Number.objects.create(num=1)
        Number.objects.create(num=2)

        Article.objects.create(name="one", created=datetime.datetime.now())
        Article.objects.create(name="two", created=datetime.datetime.now())
        Article.objects.create(name="three", created=datetime.datetime.now())
        Article.objects.create(name="four", created=datetime.datetime.now())

        food = Food.objects.create(name="spam")
        Eaten.objects.create(meal="spam with eggs", food=food)

    def test_tickets_7698_10202(self):
        # People like to slice with '0' as the high-water mark.
        self.assertSequenceEqual(Article.objects.all()[0:0], [])
        self.assertSequenceEqual(Article.objects.all()[0:0][:10], [])
        self.assertEqual(Article.objects.all()[:0].count(), 0)
        msg = "Cannot change a query once a slice has been taken."
        with self.assertRaisesMessage(TypeError, msg):
            Article.objects.all()[:0].latest("created")

    def test_empty_resultset_sql(self):
        # ticket #12192
        self.assertNumQueries(0, lambda: list(Number.objects.all()[1:1]))

    def test_empty_sliced_subquery(self):
        self.assertEqual(
            Eaten.objects.filter(food__in=Food.objects.all()[0:0]).count(), 0
        )

    def test_empty_sliced_subquery_exclude(self):
        self.assertEqual(
            Eaten.objects.exclude(food__in=Food.objects.all()[0:0]).count(), 1
        )

    def test_zero_length_values_slicing(self):
        n = 42
        with self.assertNumQueries(0):
            self.assertQuerySetEqual(Article.objects.values()[n:n], [])
            self.assertQuerySetEqual(Article.objects.values_list()[n:n], [])


class EscapingTests(TestCase):
    def test_ticket_7302(self):
        # Reserved names are appropriately escaped
        r_a = ReservedName.objects.create(name="a", order=42)
        r_b = ReservedName.objects.create(name="b", order=37)
        self.assertSequenceEqual(
            ReservedName.objects.order_by("order"),
            [r_b, r_a],
        )
        self.assertSequenceEqual(
            ReservedName.objects.extra(
                select={"stuff": "name"}, order_by=("order", "stuff")
            ),
            [r_b, r_a],
        )


class ToFieldTests(TestCase):
    def test_in_query(self):
        apple = Food.objects.create(name="apple")
        pear = Food.objects.create(name="pear")
        lunch = Eaten.objects.create(food=apple, meal="lunch")
        dinner = Eaten.objects.create(food=pear, meal="dinner")

        self.assertEqual(
            set(Eaten.objects.filter(food__in=[apple, pear])),
            {lunch, dinner},
        )

    def test_in_subquery(self):
        apple = Food.objects.create(name="apple")
        lunch = Eaten.objects.create(food=apple, meal="lunch")
        self.assertEqual(
            set(Eaten.objects.filter(food__in=Food.objects.filter(name="apple"))),
            {lunch},
        )
        self.assertEqual(
            set(
                Eaten.objects.filter(
                    food__in=Food.objects.filter(name="apple").values("eaten__meal")
                )
            ),
            set(),
        )
        self.assertEqual(
            set(Food.objects.filter(eaten__in=Eaten.objects.filter(meal="lunch"))),
            {apple},
        )

    def test_nested_in_subquery(self):
        extra = ExtraInfo.objects.create()
        author = Author.objects.create(num=42, extra=extra)
        report = Report.objects.create(creator=author)
        comment = ReportComment.objects.create(report=report)
        comments = ReportComment.objects.filter(
            report__in=Report.objects.filter(
                creator__in=extra.author_set.all(),
            ),
        )
        self.assertSequenceEqual(comments, [comment])

    def test_reverse_in(self):
        apple = Food.objects.create(name="apple")
        pear = Food.objects.create(name="pear")
        lunch_apple = Eaten.objects.create(food=apple, meal="lunch")
        lunch_pear = Eaten.objects.create(food=pear, meal="dinner")

        self.assertEqual(
            set(Food.objects.filter(eaten__in=[lunch_apple, lunch_pear])), {apple, pear}
        )

    def test_single_object(self):
        apple = Food.objects.create(name="apple")
        lunch = Eaten.objects.create(food=apple, meal="lunch")
        dinner = Eaten.objects.create(food=apple, meal="dinner")

        self.assertEqual(set(Eaten.objects.filter(food=apple)), {lunch, dinner})

    def test_single_object_reverse(self):
        apple = Food.objects.create(name="apple")
        lunch = Eaten.objects.create(food=apple, meal="lunch")

        self.assertEqual(set(Food.objects.filter(eaten=lunch)), {apple})

    def test_recursive_fk(self):
        node1 = Node.objects.create(num=42)
        node2 = Node.objects.create(num=1, parent=node1)

        self.assertEqual(list(Node.objects.filter(parent=node1)), [node2])

    def test_recursive_fk_reverse(self):
        node1 = Node.objects.create(num=42)
        node2 = Node.objects.create(num=1, parent=node1)

        self.assertEqual(list(Node.objects.filter(node=node2)), [node1])


class IsNullTests(TestCase):
    def test_primary_key(self):
        custom = CustomPk.objects.create(name="pk")
        null = Related.objects.create()
        notnull = Related.objects.create(custom=custom)
        self.assertSequenceEqual(
            Related.objects.filter(custom__isnull=False), [notnull]
        )
        self.assertSequenceEqual(Related.objects.filter(custom__isnull=True), [null])

    def test_to_field(self):
        apple = Food.objects.create(name="apple")
        e1 = Eaten.objects.create(food=apple, meal="lunch")
        e2 = Eaten.objects.create(meal="lunch")
        self.assertSequenceEqual(
            Eaten.objects.filter(food__isnull=False),
            [e1],
        )
        self.assertSequenceEqual(
            Eaten.objects.filter(food__isnull=True),
            [e2],
        )


class ConditionalTests(TestCase):
    """Tests whose execution depend on different environment conditions like
    Python version or DB backend features"""

    @classmethod
    def setUpTestData(cls):
        generic = NamedCategory.objects.create(name="Generic")
        t1 = Tag.objects.create(name="t1", category=generic)
        Tag.objects.create(name="t2", parent=t1, category=generic)
        t3 = Tag.objects.create(name="t3", parent=t1)
        Tag.objects.create(name="t4", parent=t3)
        Tag.objects.create(name="t5", parent=t3)

    def test_infinite_loop(self):
        # If you're not careful, it's possible to introduce infinite loops via
        # default ordering on foreign keys in a cycle. We detect that.
        with self.assertRaisesMessage(FieldError, "Infinite loop caused by ordering."):
            list(LoopX.objects.all())  # Force queryset evaluation with list()
        with self.assertRaisesMessage(FieldError, "Infinite loop caused by ordering."):
            list(LoopZ.objects.all())  # Force queryset evaluation with list()

        # Note that this doesn't cause an infinite loop, since the default
        # ordering on the Tag model is empty (and thus defaults to using "id"
        # for the related field).
        self.assertEqual(len(Tag.objects.order_by("parent")), 5)

        # ... but you can still order in a non-recursive fashion among linked
        # fields (the previous test failed because the default ordering was
        # recursive).
        self.assertSequenceEqual(LoopX.objects.order_by("y__x__y__x__id"), [])

    # When grouping without specifying ordering, we add an explicit "ORDER BY NULL"
    # portion in MySQL to prevent unnecessary sorting.
    @skipUnlessDBFeature("requires_explicit_null_ordering_when_grouping")
    def test_null_ordering_added(self):
        query = Tag.objects.values_list("parent_id", flat=True).order_by().query
        query.group_by = ["parent_id"]
        sql = query.get_compiler(DEFAULT_DB_ALIAS).as_sql()[0]
        fragment = "ORDER BY "
        pos = sql.find(fragment)
        self.assertEqual(sql.find(fragment, pos + 1), -1)
        self.assertEqual(sql.find("NULL", pos + len(fragment)), pos + len(fragment))

    def test_in_list_limit(self):
        # The "in" lookup works with lists of 1000 items or more.
        # The numbers amount is picked to force three different IN batches
        # for Oracle, yet to be less than 2100 parameter limit for MSSQL.
        numbers = list(range(2050))
        max_query_params = connection.features.max_query_params
        if max_query_params is None or max_query_params >= len(numbers):
            Number.objects.bulk_create(Number(num=num) for num in numbers)
            for number in [1000, 1001, 2000, len(numbers)]:
                with self.subTest(number=number):
                    self.assertEqual(
                        Number.objects.filter(num__in=numbers[:number]).count(), number
                    )


class UnionTests(unittest.TestCase):
    """
    Tests for the union of two querysets. Bug #12252.
    """

    @classmethod
    def setUpTestData(cls):
        objectas = []
        objectbs = []
        objectcs = []
        a_info = ["one", "two", "three"]
        for name in a_info:
            o = ObjectA(name=name)
            o.save()
            objectas.append(o)
        b_info = [
            ("un", 1, objectas[0]),
            ("deux", 2, objectas[0]),
            ("trois", 3, objectas[2]),
        ]
        for name, number, objecta in b_info:
            o = ObjectB(name=name, num=number, objecta=objecta)
            o.save()
            objectbs.append(o)
        c_info = [("ein", objectas[2], objectbs[2]), ("zwei", objectas[1], objectbs[1])]
        for name, objecta, objectb in c_info:
            o = ObjectC(name=name, objecta=objecta, objectb=objectb)
            o.save()
            objectcs.append(o)

    def check_union(self, model, Q1, Q2):
        filter = model.objects.filter
        self.assertEqual(set(filter(Q1) | filter(Q2)), set(filter(Q1 | Q2)))
        self.assertEqual(set(filter(Q2) | filter(Q1)), set(filter(Q1 | Q2)))

    def test_A_AB(self):
        Q1 = Q(name="two")
        Q2 = Q(objectb__name="deux")
        self.check_union(ObjectA, Q1, Q2)

    def test_A_AB2(self):
        Q1 = Q(name="two")
        Q2 = Q(objectb__name="deux", objectb__num=2)
        self.check_union(ObjectA, Q1, Q2)

    def test_AB_ACB(self):
        Q1 = Q(objectb__name="deux")
        Q2 = Q(objectc__objectb__name="deux")
        self.check_union(ObjectA, Q1, Q2)

    def test_BAB_BAC(self):
        Q1 = Q(objecta__objectb__name="deux")
        Q2 = Q(objecta__objectc__name="ein")
        self.check_union(ObjectB, Q1, Q2)

    def test_BAB_BACB(self):
        Q1 = Q(objecta__objectb__name="deux")
        Q2 = Q(objecta__objectc__objectb__name="trois")
        self.check_union(ObjectB, Q1, Q2)

    def test_BA_BCA__BAB_BAC_BCA(self):
        Q1 = Q(objecta__name="one", objectc__objecta__name="two")
        Q2 = Q(
            objecta__objectc__name="ein",
            objectc__objecta__name="three",
            objecta__objectb__name="trois",
        )
        self.check_union(ObjectB, Q1, Q2)


class DefaultValuesInsertTest(TestCase):
    def test_no_extra_params(self):
        """
        Can create an instance of a model with only the PK field (#17056)."
        """
        DumbCategory.objects.create()


class ExcludeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        f1 = Food.objects.create(name="apples")
        cls.f2 = Food.objects.create(name="oranges")
        Eaten.objects.create(food=f1, meal="dinner")
        cls.j1 = Job.objects.create(name="Manager")
        cls.r1 = Responsibility.objects.create(description="Playing golf")
        cls.j2 = Job.objects.create(name="Programmer")
        cls.r2 = Responsibility.objects.create(description="Programming")
        JobResponsibilities.objects.create(job=cls.j1, responsibility=cls.r1)
        JobResponsibilities.objects.create(job=cls.j2, responsibility=cls.r2)

    def test_to_field(self):
        self.assertSequenceEqual(
            Food.objects.exclude(eaten__meal="dinner"),
            [self.f2],
        )
        self.assertSequenceEqual(
            Job.objects.exclude(responsibilities__description="Playing golf"),
            [self.j2],
        )
        self.assertSequenceEqual(
            Responsibility.objects.exclude(jobs__name="Manager"),
            [self.r2],
        )

    def test_exclude_m2m_through(self):
        alex = Person.objects.get_or_create(name="Alex")[0]
        jane = Person.objects.get_or_create(name="Jane")[0]

        oracle = Company.objects.get_or_create(name="Oracle")[0]
        google = Company.objects.get_or_create(name="Google")[0]
        microsoft = Company.objects.get_or_create(name="Microsoft")[0]
        intel = Company.objects.get_or_create(name="Intel")[0]

        def employ(employer, employee, title):
            Employment.objects.get_or_create(
                employee=employee, employer=employer, title=title
            )

        employ(oracle, alex, "Engineer")
        employ(oracle, alex, "Developer")
        employ(google, alex, "Engineer")
        employ(google, alex, "Manager")
        employ(microsoft, alex, "Manager")
        employ(intel, alex, "Manager")

        employ(microsoft, jane, "Developer")
        employ(intel, jane, "Manager")

        alex_tech_employers = (
            alex.employers.filter(employment__title__in=("Engineer", "Developer"))
            .distinct()
            .order_by("name")
        )
        self.assertSequenceEqual(alex_tech_employers, [google, oracle])

        alex_nontech_employers = (
            alex.employers.exclude(employment__title__in=("Engineer", "Developer"))
            .distinct()
            .order_by("name")
        )
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(alex_nontech_employers, [google, intel, microsoft])
        sql = ctx.captured_queries[0]["sql"]
        # Company's ID should appear in SELECT and INNER JOIN, not in EXISTS as
        # the outer query reference is not necessary when an alias is reused.
        company_id = "%s.%s" % (
            connection.ops.quote_name(Company._meta.db_table),
            connection.ops.quote_name(Company._meta.get_field("id").column),
        )
        self.assertEqual(sql.count(company_id), 2)

    def test_exclude_reverse_fk_field_ref(self):
        tag = Tag.objects.create()
        Note.objects.create(tag=tag, note="note")
        annotation = Annotation.objects.create(name="annotation", tag=tag)
        self.assertEqual(
            Annotation.objects.exclude(tag__note__note=F("name")).get(), annotation
        )

    def test_exclude_with_circular_fk_relation(self):
        self.assertEqual(
            ObjectB.objects.exclude(objecta__objectb__name=F("name")).count(), 0
        )

    def test_subquery_exclude_outerref(self):
        qs = JobResponsibilities.objects.filter(
            Exists(Responsibility.objects.exclude(jobs=OuterRef("job"))),
        )
        self.assertTrue(qs.exists())
        self.r1.delete()
        self.assertFalse(qs.exists())

    def test_exclude_nullable_fields(self):
        number = Number.objects.create(num=1, other_num=1)
        Number.objects.create(num=2, other_num=2, another_num=2)
        self.assertSequenceEqual(
            Number.objects.exclude(other_num=F("another_num")),
            [number],
        )
        self.assertSequenceEqual(
            Number.objects.exclude(num=F("another_num")),
            [number],
        )

    def test_exclude_multivalued_exists(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.assertSequenceEqual(
                Job.objects.exclude(responsibilities__description="Programming"),
                [self.j1],
            )
        self.assertIn("exists", captured_queries[0]["sql"].lower())

    def test_exclude_subquery(self):
        subquery = JobResponsibilities.objects.filter(
            responsibility__description="bar",
        ) | JobResponsibilities.objects.exclude(
            job__responsibilities__description="foo",
        )
        self.assertCountEqual(
            Job.objects.annotate(
                responsibility=subquery.filter(job=OuterRef("name")).values("id")[:1]
            ),
            [self.j1, self.j2],
        )

    def test_exclude_unsaved_object(self):
        company = Company.objects.create(name="Django")
        msg = "Model instances passed to related filters must be saved."
        with self.assertRaisesMessage(ValueError, msg):
            Employment.objects.exclude(employer=Company(name="unsaved"))
        with self.assertRaisesMessage(ValueError, msg):
            Employment.objects.exclude(employer__in=[company, Company(name="unsaved")])
        with self.assertRaisesMessage(ValueError, msg):
            StaffUser.objects.exclude(staff=Staff(name="unsaved"))


class ExcludeTest17600(TestCase):
    """
    Some regressiontests for ticket #17600. Some of these likely duplicate
    other existing tests.
    """

    @classmethod
    def setUpTestData(cls):
        # Create a few Orders.
        cls.o1 = Order.objects.create(pk=1)
        cls.o2 = Order.objects.create(pk=2)
        cls.o3 = Order.objects.create(pk=3)

        # Create some OrderItems for the first order with homogeneous
        # status_id values
        cls.oi1 = OrderItem.objects.create(order=cls.o1, status=1)
        cls.oi2 = OrderItem.objects.create(order=cls.o1, status=1)
        cls.oi3 = OrderItem.objects.create(order=cls.o1, status=1)

        # Create some OrderItems for the second order with heterogeneous
        # status_id values
        cls.oi4 = OrderItem.objects.create(order=cls.o2, status=1)
        cls.oi5 = OrderItem.objects.create(order=cls.o2, status=2)
        cls.oi6 = OrderItem.objects.create(order=cls.o2, status=3)

        # Create some OrderItems for the second order with heterogeneous
        # status_id values
        cls.oi7 = OrderItem.objects.create(order=cls.o3, status=2)
        cls.oi8 = OrderItem.objects.create(order=cls.o3, status=3)
        cls.oi9 = OrderItem.objects.create(order=cls.o3, status=4)

    def test_exclude_plain(self):
        """
        This should exclude Orders which have some items with status 1
        """
        self.assertSequenceEqual(
            Order.objects.exclude(items__status=1),
            [self.o3],
        )

    def test_exclude_plain_distinct(self):
        """
        This should exclude Orders which have some items with status 1
        """
        self.assertSequenceEqual(
            Order.objects.exclude(items__status=1).distinct(),
            [self.o3],
        )

    def test_exclude_with_q_object_distinct(self):
        """
        This should exclude Orders which have some items with status 1
        """
        self.assertSequenceEqual(
            Order.objects.exclude(Q(items__status=1)).distinct(),
            [self.o3],
        )

    def test_exclude_with_q_object_no_distinct(self):
        """
        This should exclude Orders which have some items with status 1
        """
        self.assertSequenceEqual(
            Order.objects.exclude(Q(items__status=1)),
            [self.o3],
        )

    def test_exclude_with_q_is_equal_to_plain_exclude(self):
        """
        Using exclude(condition) and exclude(Q(condition)) should
        yield the same QuerySet
        """
        self.assertEqual(
            list(Order.objects.exclude(items__status=1).distinct()),
            list(Order.objects.exclude(Q(items__status=1)).distinct()),
        )

    def test_exclude_with_q_is_equal_to_plain_exclude_variation(self):
        """
        Using exclude(condition) and exclude(Q(condition)) should
        yield the same QuerySet
        """
        self.assertEqual(
            list(Order.objects.exclude(items__status=1)),
            list(Order.objects.exclude(Q(items__status=1)).distinct()),
        )

    @unittest.expectedFailure
    def test_only_orders_with_all_items_having_status_1(self):
        """
        This should only return orders having ALL items set to status 1, or
        those items not having any orders at all. The correct way to write
        this query in SQL seems to be using two nested subqueries.
        """
        self.assertSequenceEqual(
            Order.objects.exclude(~Q(items__status=1)).distinct(),
            [self.o1],
        )


class Exclude15786(TestCase):
    """Regression test for #15786"""

    def test_ticket15786(self):
        c1 = SimpleCategory.objects.create(name="c1")
        c2 = SimpleCategory.objects.create(name="c2")
        OneToOneCategory.objects.create(category=c1)
        OneToOneCategory.objects.create(category=c2)
        rel = CategoryRelationship.objects.create(first=c1, second=c2)
        self.assertEqual(
            CategoryRelationship.objects.exclude(
                first__onetoonecategory=F("second__onetoonecategory")
            ).get(),
            rel,
        )


class NullInExcludeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        NullableName.objects.create(name="i1")
        NullableName.objects.create()

    def test_null_in_exclude_qs(self):
        none_val = "" if connection.features.interprets_empty_strings_as_nulls else None
        self.assertQuerySetEqual(
            NullableName.objects.exclude(name__in=[]),
            ["i1", none_val],
            attrgetter("name"),
        )
        self.assertQuerySetEqual(
            NullableName.objects.exclude(name__in=["i1"]),
            [none_val],
            attrgetter("name"),
        )
        self.assertQuerySetEqual(
            NullableName.objects.exclude(name__in=["i3"]),
            ["i1", none_val],
            attrgetter("name"),
        )
        inner_qs = NullableName.objects.filter(name="i1").values_list("name")
        self.assertQuerySetEqual(
            NullableName.objects.exclude(name__in=inner_qs),
            [none_val],
            attrgetter("name"),
        )
        # The inner queryset wasn't executed - it should be turned
        # into subquery above
        self.assertIs(inner_qs._result_cache, None)

    @unittest.expectedFailure
    def test_col_not_in_list_containing_null(self):
        """
        The following case is not handled properly because
        SQL's COL NOT IN (list containing null) handling is too weird to
        abstract away.
        """
        self.assertQuerySetEqual(
            NullableName.objects.exclude(name__in=[None]), ["i1"], attrgetter("name")
        )

    def test_double_exclude(self):
        self.assertEqual(
            list(NullableName.objects.filter(~~Q(name="i1"))),
            list(NullableName.objects.filter(Q(name="i1"))),
        )
        self.assertNotIn(
            "IS NOT NULL", str(NullableName.objects.filter(~~Q(name="i1")).query)
        )


class EmptyStringsAsNullTest(TestCase):
    """
    Filtering on non-null character fields works as expected.
    The reason for these tests is that Oracle treats '' as NULL, and this
    can cause problems in query construction. Refs #17957.
    """

    @classmethod
    def setUpTestData(cls):
        cls.nc = NamedCategory.objects.create(name="")

    def test_direct_exclude(self):
        self.assertQuerySetEqual(
            NamedCategory.objects.exclude(name__in=["nonexistent"]),
            [self.nc.pk],
            attrgetter("pk"),
        )

    def test_joined_exclude(self):
        self.assertQuerySetEqual(
            DumbCategory.objects.exclude(namedcategory__name__in=["nonexistent"]),
            [self.nc.pk],
            attrgetter("pk"),
        )

    def test_21001(self):
        foo = NamedCategory.objects.create(name="foo")
        self.assertQuerySetEqual(
            NamedCategory.objects.exclude(name=""), [foo.pk], attrgetter("pk")
        )


class ProxyQueryCleanupTest(TestCase):
    def test_evaluated_proxy_count(self):
        """
        Generating the query string doesn't alter the query's state
        in irreversible ways. Refs #18248.
        """
        ProxyCategory.objects.create()
        qs = ProxyCategory.objects.all()
        self.assertEqual(qs.count(), 1)
        str(qs.query)
        self.assertEqual(qs.count(), 1)


class WhereNodeTest(SimpleTestCase):
    class DummyNode:
        def as_sql(self, compiler, connection):
            return "dummy", []

    class MockCompiler:
        def compile(self, node):
            return node.as_sql(self, connection)

        def __call__(self, name):
            return connection.ops.quote_name(name)

    def test_empty_full_handling_conjunction(self):
        compiler = WhereNodeTest.MockCompiler()
        w = WhereNode(children=[NothingNode()])
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)
        w.negate()
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)
        w = WhereNode(children=[self.DummyNode(), self.DummyNode()])
        self.assertEqual(w.as_sql(compiler, connection), ("(dummy AND dummy)", []))
        w.negate()
        self.assertEqual(w.as_sql(compiler, connection), ("NOT (dummy AND dummy)", []))
        w = WhereNode(children=[NothingNode(), self.DummyNode()])
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)
        w.negate()
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)

    def test_empty_full_handling_disjunction(self):
        compiler = WhereNodeTest.MockCompiler()
        w = WhereNode(children=[NothingNode()], connector=OR)
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)
        w.negate()
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)
        w = WhereNode(children=[self.DummyNode(), self.DummyNode()], connector=OR)
        self.assertEqual(w.as_sql(compiler, connection), ("(dummy OR dummy)", []))
        w.negate()
        self.assertEqual(w.as_sql(compiler, connection), ("NOT (dummy OR dummy)", []))
        w = WhereNode(children=[NothingNode(), self.DummyNode()], connector=OR)
        self.assertEqual(w.as_sql(compiler, connection), ("dummy", []))
        w.negate()
        self.assertEqual(w.as_sql(compiler, connection), ("NOT (dummy)", []))

    def test_empty_nodes(self):
        compiler = WhereNodeTest.MockCompiler()
        empty_w = WhereNode()
        w = WhereNode(children=[empty_w, empty_w])
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)
        w.negate()
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)
        w.connector = OR
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)
        w.negate()
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)
        w = WhereNode(children=[empty_w, NothingNode()], connector=OR)
        with self.assertRaises(FullResultSet):
            w.as_sql(compiler, connection)
        w = WhereNode(children=[empty_w, NothingNode()], connector=AND)
        with self.assertRaises(EmptyResultSet):
            w.as_sql(compiler, connection)


class QuerySetExceptionTests(SimpleTestCase):
    def test_invalid_order_by(self):
        msg = "Cannot resolve keyword '*' into field. Choices are: created, id, name"
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.order_by("*")

    def test_invalid_order_by_raw_column_alias(self):
        msg = (
            "Cannot resolve keyword 'queries_author.name' into field. Choices "
            "are: cover, created, creator, creator_id, id, modified, name, "
            "note, note_id, tags"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Item.objects.values("creator__name").order_by("queries_author.name")

    def test_invalid_queryset_model(self):
        msg = 'Cannot use QuerySet for "Article": Use a QuerySet for "ExtraInfo".'
        with self.assertRaisesMessage(ValueError, msg):
            list(Author.objects.filter(extra=Article.objects.all()))


class NullJoinPromotionOrTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d1 = ModelD.objects.create(name="foo")
        d2 = ModelD.objects.create(name="bar")
        cls.a1 = ModelA.objects.create(name="a1", d=cls.d1)
        c = ModelC.objects.create(name="c")
        b = ModelB.objects.create(name="b", c=c)
        cls.a2 = ModelA.objects.create(name="a2", b=b, d=d2)

    def test_ticket_17886(self):
        # The first Q-object is generating the match, the rest of the filters
        # should not remove the match even if they do not match anything. The
        # problem here was that b__name generates a LOUTER JOIN, then
        # b__c__name generates join to c, which the ORM tried to promote but
        # failed as that join isn't nullable.
        q_obj = Q(d__name="foo") | Q(b__name="foo") | Q(b__c__name="foo")
        qset = ModelA.objects.filter(q_obj)
        self.assertEqual(list(qset), [self.a1])
        # We generate one INNER JOIN to D. The join is direct and not nullable
        # so we can use INNER JOIN for it. However, we can NOT use INNER JOIN
        # for the b->c join, as a->b is nullable.
        self.assertEqual(str(qset.query).count("INNER JOIN"), 1)

    def test_isnull_filter_promotion(self):
        qs = ModelA.objects.filter(Q(b__name__isnull=True))
        self.assertEqual(str(qs.query).count("LEFT OUTER"), 1)
        self.assertEqual(list(qs), [self.a1])

        qs = ModelA.objects.filter(~Q(b__name__isnull=True))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(list(qs), [self.a2])

        qs = ModelA.objects.filter(~~Q(b__name__isnull=True))
        self.assertEqual(str(qs.query).count("LEFT OUTER"), 1)
        self.assertEqual(list(qs), [self.a1])

        qs = ModelA.objects.filter(Q(b__name__isnull=False))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(list(qs), [self.a2])

        qs = ModelA.objects.filter(~Q(b__name__isnull=False))
        self.assertEqual(str(qs.query).count("LEFT OUTER"), 1)
        self.assertEqual(list(qs), [self.a1])

        qs = ModelA.objects.filter(~~Q(b__name__isnull=False))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(list(qs), [self.a2])

    def test_null_join_demotion(self):
        qs = ModelA.objects.filter(Q(b__name__isnull=False) & Q(b__name__isnull=True))
        self.assertIn(" INNER JOIN ", str(qs.query))
        qs = ModelA.objects.filter(Q(b__name__isnull=True) & Q(b__name__isnull=False))
        self.assertIn(" INNER JOIN ", str(qs.query))
        qs = ModelA.objects.filter(Q(b__name__isnull=False) | Q(b__name__isnull=True))
        self.assertIn(" LEFT OUTER JOIN ", str(qs.query))
        qs = ModelA.objects.filter(Q(b__name__isnull=True) | Q(b__name__isnull=False))
        self.assertIn(" LEFT OUTER JOIN ", str(qs.query))

    def test_ticket_21366(self):
        n = Note.objects.create(note="n", misc="m")
        e = ExtraInfo.objects.create(info="info", note=n)
        a = Author.objects.create(name="Author1", num=1, extra=e)
        Ranking.objects.create(rank=1, author=a)
        r1 = Report.objects.create(name="Foo", creator=a)
        r2 = Report.objects.create(name="Bar")
        Report.objects.create(name="Bar", creator=a)
        qs = Report.objects.filter(
            Q(creator__ranking__isnull=True) | Q(creator__ranking__rank=1, name="Foo")
        )
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        self.assertEqual(str(qs.query).count(" JOIN "), 2)
        self.assertSequenceEqual(qs.order_by("name"), [r2, r1])

    def test_ticket_21748(self):
        i1 = Identifier.objects.create(name="i1")
        i2 = Identifier.objects.create(name="i2")
        i3 = Identifier.objects.create(name="i3")
        Program.objects.create(identifier=i1)
        Channel.objects.create(identifier=i1)
        Program.objects.create(identifier=i2)
        self.assertSequenceEqual(
            Identifier.objects.filter(program=None, channel=None), [i3]
        )
        self.assertSequenceEqual(
            Identifier.objects.exclude(program=None, channel=None).order_by("name"),
            [i1, i2],
        )

    def test_ticket_21748_double_negated_and(self):
        i1 = Identifier.objects.create(name="i1")
        i2 = Identifier.objects.create(name="i2")
        Identifier.objects.create(name="i3")
        p1 = Program.objects.create(identifier=i1)
        c1 = Channel.objects.create(identifier=i1)
        Program.objects.create(identifier=i2)
        # Check the ~~Q() (or equivalently .exclude(~Q)) works like Q() for
        # join promotion.
        qs1_doubleneg = Identifier.objects.exclude(
            ~Q(program__id=p1.id, channel__id=c1.id)
        ).order_by("pk")
        qs1_filter = Identifier.objects.filter(
            program__id=p1.id, channel__id=c1.id
        ).order_by("pk")
        self.assertQuerySetEqual(qs1_doubleneg, qs1_filter, lambda x: x)
        self.assertEqual(
            str(qs1_filter.query).count("JOIN"), str(qs1_doubleneg.query).count("JOIN")
        )
        self.assertEqual(2, str(qs1_doubleneg.query).count("INNER JOIN"))
        self.assertEqual(
            str(qs1_filter.query).count("INNER JOIN"),
            str(qs1_doubleneg.query).count("INNER JOIN"),
        )

    def test_ticket_21748_double_negated_or(self):
        i1 = Identifier.objects.create(name="i1")
        i2 = Identifier.objects.create(name="i2")
        Identifier.objects.create(name="i3")
        p1 = Program.objects.create(identifier=i1)
        c1 = Channel.objects.create(identifier=i1)
        p2 = Program.objects.create(identifier=i2)
        # Test OR + doubleneg. The expected result is that channel is LOUTER
        # joined, program INNER joined
        qs1_filter = Identifier.objects.filter(
            Q(program__id=p2.id, channel__id=c1.id) | Q(program__id=p1.id)
        ).order_by("pk")
        qs1_doubleneg = Identifier.objects.exclude(
            ~Q(Q(program__id=p2.id, channel__id=c1.id) | Q(program__id=p1.id))
        ).order_by("pk")
        self.assertQuerySetEqual(qs1_doubleneg, qs1_filter, lambda x: x)
        self.assertEqual(
            str(qs1_filter.query).count("JOIN"), str(qs1_doubleneg.query).count("JOIN")
        )
        self.assertEqual(1, str(qs1_doubleneg.query).count("INNER JOIN"))
        self.assertEqual(
            str(qs1_filter.query).count("INNER JOIN"),
            str(qs1_doubleneg.query).count("INNER JOIN"),
        )

    def test_ticket_21748_complex_filter(self):
        i1 = Identifier.objects.create(name="i1")
        i2 = Identifier.objects.create(name="i2")
        Identifier.objects.create(name="i3")
        p1 = Program.objects.create(identifier=i1)
        c1 = Channel.objects.create(identifier=i1)
        p2 = Program.objects.create(identifier=i2)
        # Finally, a more complex case, one time in a way where each
        # NOT is pushed to lowest level in the boolean tree, and
        # another query where this isn't done.
        qs1 = Identifier.objects.filter(
            ~Q(~Q(program__id=p2.id, channel__id=c1.id) & Q(program__id=p1.id))
        ).order_by("pk")
        qs2 = Identifier.objects.filter(
            Q(Q(program__id=p2.id, channel__id=c1.id) | ~Q(program__id=p1.id))
        ).order_by("pk")
        self.assertQuerySetEqual(qs1, qs2, lambda x: x)
        self.assertEqual(str(qs1.query).count("JOIN"), str(qs2.query).count("JOIN"))
        self.assertEqual(0, str(qs1.query).count("INNER JOIN"))
        self.assertEqual(
            str(qs1.query).count("INNER JOIN"), str(qs2.query).count("INNER JOIN")
        )


class ReverseJoinTrimmingTest(TestCase):
    def test_reverse_trimming(self):
        # We don't accidentally trim reverse joins - we can't know if there is
        # anything on the other side of the join, so trimming reverse joins
        # can't be done, ever.
        t = Tag.objects.create()
        qs = Tag.objects.filter(annotation__tag=t.pk)
        self.assertIn("INNER JOIN", str(qs.query))
        self.assertEqual(list(qs), [])


class JoinReuseTest(TestCase):
    """
    The queries reuse joins sensibly (for example, direct joins
    are always reused).
    """

    def test_fk_reuse(self):
        qs = Annotation.objects.filter(tag__name="foo").filter(tag__name="bar")
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_fk_reuse_select_related(self):
        qs = Annotation.objects.filter(tag__name="foo").select_related("tag")
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_fk_reuse_annotation(self):
        qs = Annotation.objects.filter(tag__name="foo").annotate(cnt=Count("tag__name"))
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_fk_reuse_disjunction(self):
        qs = Annotation.objects.filter(Q(tag__name="foo") | Q(tag__name="bar"))
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_fk_reuse_order_by(self):
        qs = Annotation.objects.filter(tag__name="foo").order_by("tag__name")
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_revo2o_reuse(self):
        qs = Detail.objects.filter(member__name="foo").filter(member__name="foo")
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_revfk_noreuse(self):
        qs = Author.objects.filter(report__name="r4").filter(report__name="r1")
        self.assertEqual(str(qs.query).count("JOIN"), 2)

    def test_inverted_q_across_relations(self):
        """
        When a trimmable join is specified in the query (here school__), the
        ORM detects it and removes unnecessary joins. The set of reusable joins
        are updated after trimming the query so that other lookups don't
        consider that the outer query's filters are in effect for the subquery
        (#26551).
        """
        springfield_elementary = School.objects.create()
        hogward = School.objects.create()
        Student.objects.create(school=springfield_elementary)
        hp = Student.objects.create(school=hogward)
        Classroom.objects.create(school=hogward, name="Potion")
        Classroom.objects.create(school=springfield_elementary, name="Main")
        qs = Student.objects.filter(
            ~(
                Q(school__classroom__name="Main")
                & Q(school__classroom__has_blackboard=None)
            )
        )
        self.assertSequenceEqual(qs, [hp])


class DisjunctionPromotionTests(TestCase):
    def test_disjunction_promotion_select_related(self):
        fk1 = FK1.objects.create(f1="f1", f2="f2")
        basea = BaseA.objects.create(a=fk1)
        qs = BaseA.objects.filter(Q(a=fk1) | Q(b=2))
        self.assertEqual(str(qs.query).count(" JOIN "), 0)
        qs = qs.select_related("a", "b")
        self.assertEqual(str(qs.query).count(" INNER JOIN "), 0)
        self.assertEqual(str(qs.query).count(" LEFT OUTER JOIN "), 2)
        with self.assertNumQueries(1):
            self.assertSequenceEqual(qs, [basea])
            self.assertEqual(qs[0].a, fk1)
            self.assertIs(qs[0].b, None)

    def test_disjunction_promotion1(self):
        # Pre-existing join, add two ORed filters to the same join,
        # all joins can be INNER JOINS.
        qs = BaseA.objects.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        qs = qs.filter(Q(b__f1="foo") | Q(b__f2="foo"))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 2)
        # Reverse the order of AND and OR filters.
        qs = BaseA.objects.filter(Q(b__f1="foo") | Q(b__f2="foo"))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        qs = qs.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 2)

    def test_disjunction_promotion2(self):
        qs = BaseA.objects.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        # Now we have two different joins in an ORed condition, these
        # must be OUTER joins. The pre-existing join should remain INNER.
        qs = qs.filter(Q(b__f1="foo") | Q(c__f2="foo"))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        # Reverse case.
        qs = BaseA.objects.filter(Q(b__f1="foo") | Q(c__f2="foo"))
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        qs = qs.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)

    def test_disjunction_promotion3(self):
        qs = BaseA.objects.filter(a__f2="bar")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        # The ANDed a__f2 filter allows us to use keep using INNER JOIN
        # even inside the ORed case. If the join to a__ returns nothing,
        # the ANDed filter for a__f2 can't be true.
        qs = qs.filter(Q(a__f1="foo") | Q(b__f2="foo"))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)

    def test_disjunction_promotion3_demote(self):
        # This one needs demotion logic: the first filter causes a to be
        # outer joined, the second filter makes it inner join again.
        qs = BaseA.objects.filter(Q(a__f1="foo") | Q(b__f2="foo")).filter(a__f2="bar")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)

    def test_disjunction_promotion4_demote(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("JOIN"), 0)
        # Demote needed for the "a" join. It is marked as outer join by
        # above filter (even if it is trimmed away).
        qs = qs.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)

    def test_disjunction_promotion4(self):
        qs = BaseA.objects.filter(a__f1="foo")
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        qs = qs.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)

    def test_disjunction_promotion5_demote(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        # Note that the above filters on a force the join to an
        # inner join even if it is trimmed.
        self.assertEqual(str(qs.query).count("JOIN"), 0)
        qs = qs.filter(Q(a__f1="foo") | Q(b__f1="foo"))
        # So, now the a__f1 join doesn't need promotion.
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        # But b__f1 does.
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)
        qs = BaseA.objects.filter(Q(a__f1="foo") | Q(b__f1="foo"))
        # Now the join to a is created as LOUTER
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        qs = qs.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)

    def test_disjunction_promotion6(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("JOIN"), 0)
        qs = BaseA.objects.filter(Q(a__f1="foo") & Q(b__f1="foo"))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 2)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 0)

        qs = BaseA.objects.filter(Q(a__f1="foo") & Q(b__f1="foo"))
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 0)
        self.assertEqual(str(qs.query).count("INNER JOIN"), 2)
        qs = qs.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 2)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 0)

    def test_disjunction_promotion7(self):
        qs = BaseA.objects.filter(Q(a=1) | Q(a=2))
        self.assertEqual(str(qs.query).count("JOIN"), 0)
        qs = BaseA.objects.filter(Q(a__f1="foo") | (Q(b__f1="foo") & Q(a__f1="bar")))
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)
        qs = BaseA.objects.filter(
            (Q(a__f1="foo") | Q(b__f1="foo")) & (Q(a__f1="bar") | Q(c__f1="foo"))
        )
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 3)
        self.assertEqual(str(qs.query).count("INNER JOIN"), 0)
        qs = BaseA.objects.filter(
            Q(a__f1="foo") | Q(a__f1="bar") & (Q(b__f1="bar") | Q(c__f1="foo"))
        )
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)

    def test_disjunction_promotion_fexpression(self):
        qs = BaseA.objects.filter(Q(a__f1=F("b__f1")) | Q(b__f1="foo"))
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 1)
        self.assertEqual(str(qs.query).count("INNER JOIN"), 1)
        qs = BaseA.objects.filter(Q(a__f1=F("c__f1")) | Q(b__f1="foo"))
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 3)
        qs = BaseA.objects.filter(
            Q(a__f1=F("b__f1")) | Q(a__f2=F("b__f2")) | Q(c__f1="foo")
        )
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 3)
        qs = BaseA.objects.filter(Q(a__f1=F("c__f1")) | (Q(pk=1) & Q(pk=2)))
        self.assertEqual(str(qs.query).count("LEFT OUTER JOIN"), 2)
        self.assertEqual(str(qs.query).count("INNER JOIN"), 0)


class ManyToManyExcludeTest(TestCase):
    def test_exclude_many_to_many(self):
        i_extra = Identifier.objects.create(name="extra")
        i_program = Identifier.objects.create(name="program")
        program = Program.objects.create(identifier=i_program)
        i_channel = Identifier.objects.create(name="channel")
        channel = Channel.objects.create(identifier=i_channel)
        channel.programs.add(program)

        # channel contains 'program1', so all Identifiers except that one
        # should be returned
        self.assertSequenceEqual(
            Identifier.objects.exclude(program__channel=channel).order_by("name"),
            [i_channel, i_extra],
        )
        self.assertSequenceEqual(
            Identifier.objects.exclude(program__channel=None).order_by("name"),
            [i_program],
        )

    def test_ticket_12823(self):
        pg3 = Page.objects.create(text="pg3")
        pg2 = Page.objects.create(text="pg2")
        pg1 = Page.objects.create(text="pg1")
        pa1 = Paragraph.objects.create(text="pa1")
        pa1.page.set([pg1, pg2])
        pa2 = Paragraph.objects.create(text="pa2")
        pa2.page.set([pg2, pg3])
        pa3 = Paragraph.objects.create(text="pa3")
        ch1 = Chapter.objects.create(title="ch1", paragraph=pa1)
        ch2 = Chapter.objects.create(title="ch2", paragraph=pa2)
        ch3 = Chapter.objects.create(title="ch3", paragraph=pa3)
        b1 = Book.objects.create(title="b1", chapter=ch1)
        b2 = Book.objects.create(title="b2", chapter=ch2)
        b3 = Book.objects.create(title="b3", chapter=ch3)
        q = Book.objects.exclude(chapter__paragraph__page__text="pg1")
        self.assertNotIn("IS NOT NULL", str(q.query))
        self.assertEqual(len(q), 2)
        self.assertNotIn(b1, q)
        self.assertIn(b2, q)
        self.assertIn(b3, q)


class RelabelCloneTest(TestCase):
    def test_ticket_19964(self):
        my1 = MyObject.objects.create(data="foo")
        my1.parent = my1
        my1.save()
        my2 = MyObject.objects.create(data="bar", parent=my1)
        parents = MyObject.objects.filter(parent=F("id"))
        children = MyObject.objects.filter(parent__in=parents).exclude(parent=F("id"))
        self.assertEqual(list(parents), [my1])
        # Evaluating the children query (which has parents as part of it) does
        # not change results for the parents query.
        self.assertEqual(list(children), [my2])
        self.assertEqual(list(parents), [my1])


class Ticket20101Tests(TestCase):
    def test_ticket_20101(self):
        """
        Tests QuerySet ORed combining in exclude subquery case.
        """
        t = Tag.objects.create(name="foo")
        a1 = Annotation.objects.create(tag=t, name="a1")
        a2 = Annotation.objects.create(tag=t, name="a2")
        a3 = Annotation.objects.create(tag=t, name="a3")
        n = Note.objects.create(note="foo", misc="bar")
        qs1 = Note.objects.exclude(annotation__in=[a1, a2])
        qs2 = Note.objects.filter(annotation__in=[a3])
        self.assertIn(n, qs1)
        self.assertNotIn(n, qs2)
        self.assertIn(n, (qs1 | qs2))


class EmptyStringPromotionTests(SimpleTestCase):
    def test_empty_string_promotion(self):
        qs = RelatedObject.objects.filter(single__name="")
        if connection.features.interprets_empty_strings_as_nulls:
            self.assertIn("LEFT OUTER JOIN", str(qs.query))
        else:
            self.assertNotIn("LEFT OUTER JOIN", str(qs.query))


class ValuesSubqueryTests(TestCase):
    def test_values_in_subquery(self):
        # If a values() queryset is used, then the given values
        # will be used instead of forcing use of the relation's field.
        o1 = Order.objects.create(id=-2)
        o2 = Order.objects.create(id=-1)
        oi1 = OrderItem.objects.create(order=o1, status=0)
        oi1.status = oi1.pk
        oi1.save()
        OrderItem.objects.create(order=o2, status=0)

        # The query below should match o1 as it has related order_item
        # with id == status.
        self.assertSequenceEqual(
            Order.objects.filter(items__in=OrderItem.objects.values_list("status")),
            [o1],
        )


class DoubleInSubqueryTests(TestCase):
    def test_double_subquery_in(self):
        lfa1 = LeafA.objects.create(data="foo")
        lfa2 = LeafA.objects.create(data="bar")
        lfb1 = LeafB.objects.create(data="lfb1")
        lfb2 = LeafB.objects.create(data="lfb2")
        Join.objects.create(a=lfa1, b=lfb1)
        Join.objects.create(a=lfa2, b=lfb2)
        leaf_as = LeafA.objects.filter(data="foo").values_list("pk", flat=True)
        joins = Join.objects.filter(a__in=leaf_as).values_list("b__id", flat=True)
        qs = LeafB.objects.filter(pk__in=joins)
        self.assertSequenceEqual(qs, [lfb1])


class Ticket18785Tests(SimpleTestCase):
    def test_ticket_18785(self):
        # Test join trimming from ticket18785
        qs = (
            Item.objects.exclude(note__isnull=False)
            .filter(name="something", creator__extra__isnull=True)
            .order_by()
        )
        self.assertEqual(1, str(qs.query).count("INNER JOIN"))
        self.assertEqual(0, str(qs.query).count("OUTER JOIN"))


class Ticket20788Tests(TestCase):
    def test_ticket_20788(self):
        Paragraph.objects.create()
        paragraph = Paragraph.objects.create()
        page = paragraph.page.create()
        chapter = Chapter.objects.create(paragraph=paragraph)
        Book.objects.create(chapter=chapter)

        paragraph2 = Paragraph.objects.create()
        Page.objects.create()
        chapter2 = Chapter.objects.create(paragraph=paragraph2)
        book2 = Book.objects.create(chapter=chapter2)

        sentences_not_in_pub = Book.objects.exclude(chapter__paragraph__page=page)
        self.assertSequenceEqual(sentences_not_in_pub, [book2])


class Ticket12807Tests(TestCase):
    def test_ticket_12807(self):
        p1 = Paragraph.objects.create()
        p2 = Paragraph.objects.create()
        # The ORed condition below should have no effect on the query - the
        # ~Q(pk__in=[]) will always be True.
        qs = Paragraph.objects.filter((Q(pk=p2.pk) | ~Q(pk__in=[])) & Q(pk=p1.pk))
        self.assertSequenceEqual(qs, [p1])


class RelatedLookupTypeTests(TestCase):
    error = 'Cannot query "%s": Must be "%s" instance.'

    @classmethod
    def setUpTestData(cls):
        cls.oa = ObjectA.objects.create(name="oa")
        cls.poa = ProxyObjectA.objects.get(name="oa")
        cls.coa = ChildObjectA.objects.create(name="coa")
        cls.wrong_type = Order.objects.create(id=cls.oa.pk)
        cls.ob = ObjectB.objects.create(name="ob", objecta=cls.oa, num=1)
        cls.pob1 = ProxyObjectB.objects.create(name="pob", objecta=cls.oa, num=2)
        cls.pob = ProxyObjectB.objects.all()
        cls.c = ObjectC.objects.create(childobjecta=cls.coa)

    def test_wrong_type_lookup(self):
        """
        A ValueError is raised when the incorrect object type is passed to a
        query lookup.
        """
        # Passing incorrect object type
        with self.assertRaisesMessage(
            ValueError, self.error % (self.wrong_type, ObjectA._meta.object_name)
        ):
            ObjectB.objects.get(objecta=self.wrong_type)

        with self.assertRaisesMessage(
            ValueError, self.error % (self.wrong_type, ObjectA._meta.object_name)
        ):
            ObjectB.objects.filter(objecta__in=[self.wrong_type])

        with self.assertRaisesMessage(
            ValueError, self.error % (self.wrong_type, ObjectA._meta.object_name)
        ):
            ObjectB.objects.filter(objecta=self.wrong_type)

        with self.assertRaisesMessage(
            ValueError, self.error % (self.wrong_type, ObjectB._meta.object_name)
        ):
            ObjectA.objects.filter(objectb__in=[self.wrong_type, self.ob])

        # Passing an object of the class on which query is done.
        with self.assertRaisesMessage(
            ValueError, self.error % (self.ob, ObjectA._meta.object_name)
        ):
            ObjectB.objects.filter(objecta__in=[self.poa, self.ob])

        with self.assertRaisesMessage(
            ValueError, self.error % (self.ob, ChildObjectA._meta.object_name)
        ):
            ObjectC.objects.exclude(childobjecta__in=[self.coa, self.ob])

    def test_wrong_backward_lookup(self):
        """
        A ValueError is raised when the incorrect object type is passed to a
        query lookup for backward relations.
        """
        with self.assertRaisesMessage(
            ValueError, self.error % (self.oa, ObjectB._meta.object_name)
        ):
            ObjectA.objects.filter(objectb__in=[self.oa, self.ob])

        with self.assertRaisesMessage(
            ValueError, self.error % (self.oa, ObjectB._meta.object_name)
        ):
            ObjectA.objects.exclude(objectb=self.oa)

        with self.assertRaisesMessage(
            ValueError, self.error % (self.wrong_type, ObjectB._meta.object_name)
        ):
            ObjectA.objects.get(objectb=self.wrong_type)

    def test_correct_lookup(self):
        """
        When passing proxy model objects, child objects, or parent objects,
        lookups work fine.
        """
        out_a = [self.oa]
        out_b = [self.ob, self.pob1]
        out_c = [self.c]

        # proxy model objects
        self.assertSequenceEqual(
            ObjectB.objects.filter(objecta=self.poa).order_by("name"), out_b
        )
        self.assertSequenceEqual(
            ObjectA.objects.filter(objectb__in=self.pob).order_by("pk"), out_a * 2
        )

        # child objects
        self.assertSequenceEqual(ObjectB.objects.filter(objecta__in=[self.coa]), [])
        self.assertSequenceEqual(
            ObjectB.objects.filter(objecta__in=[self.poa, self.coa]).order_by("name"),
            out_b,
        )
        self.assertSequenceEqual(
            ObjectB.objects.filter(objecta__in=iter([self.poa, self.coa])).order_by(
                "name"
            ),
            out_b,
        )

        # parent objects
        self.assertSequenceEqual(ObjectC.objects.exclude(childobjecta=self.oa), out_c)

        # QuerySet related object type checking shouldn't issue queries
        # (the querysets aren't evaluated here, hence zero queries) (#23266).
        with self.assertNumQueries(0):
            ObjectB.objects.filter(objecta__in=ObjectA.objects.all())

    def test_values_queryset_lookup(self):
        """
        ValueQuerySets are not checked for compatibility with the lookup field.
        """
        # Make sure the num and objecta field values match.
        ob = ObjectB.objects.get(name="ob")
        ob.num = ob.objecta.pk
        ob.save()
        pob = ObjectB.objects.get(name="pob")
        pob.num = pob.objecta.pk
        pob.save()
        self.assertSequenceEqual(
            ObjectB.objects.filter(
                objecta__in=ObjectB.objects.values_list("num")
            ).order_by("pk"),
            [ob, pob],
        )


class Ticket14056Tests(TestCase):
    def test_ticket_14056(self):
        s1 = SharedConnection.objects.create(data="s1")
        s2 = SharedConnection.objects.create(data="s2")
        s3 = SharedConnection.objects.create(data="s3")
        PointerA.objects.create(connection=s2)
        expected_ordering = (
            [s1, s3, s2] if connection.features.nulls_order_largest else [s2, s1, s3]
        )
        self.assertSequenceEqual(
            SharedConnection.objects.order_by("-pointera__connection", "pk"),
            expected_ordering,
        )


class Ticket20955Tests(TestCase):
    def test_ticket_20955(self):
        jack = Staff.objects.create(name="jackstaff")
        jackstaff = StaffUser.objects.create(staff=jack)
        jill = Staff.objects.create(name="jillstaff")
        jillstaff = StaffUser.objects.create(staff=jill)
        task = Task.objects.create(creator=jackstaff, owner=jillstaff, title="task")
        task_get = Task.objects.get(pk=task.pk)
        # Load data so that assertNumQueries doesn't complain about the get
        # version's queries.
        task_get.creator.staffuser.staff
        task_get.owner.staffuser.staff
        qs = Task.objects.select_related(
            "creator__staffuser__staff", "owner__staffuser__staff"
        )
        self.assertEqual(str(qs.query).count(" JOIN "), 6)
        task_select_related = qs.get(pk=task.pk)
        with self.assertNumQueries(0):
            self.assertEqual(
                task_select_related.creator.staffuser.staff,
                task_get.creator.staffuser.staff,
            )
            self.assertEqual(
                task_select_related.owner.staffuser.staff,
                task_get.owner.staffuser.staff,
            )


class Ticket21203Tests(TestCase):
    def test_ticket_21203(self):
        p = Ticket21203Parent.objects.create(parent_bool=True)
        c = Ticket21203Child.objects.create(parent=p)
        qs = Ticket21203Child.objects.select_related("parent").defer("parent__created")
        self.assertSequenceEqual(qs, [c])
        self.assertIs(qs[0].parent.parent_bool, True)


class ValuesJoinPromotionTests(TestCase):
    def test_values_no_promotion_for_existing(self):
        qs = Node.objects.filter(parent__parent__isnull=False)
        self.assertIn(" INNER JOIN ", str(qs.query))
        qs = qs.values("parent__parent__id")
        self.assertIn(" INNER JOIN ", str(qs.query))
        # Make sure there is a left outer join without the filter.
        qs = Node.objects.values("parent__parent__id")
        self.assertIn(" LEFT OUTER JOIN ", str(qs.query))

    def test_non_nullable_fk_not_promoted(self):
        qs = ObjectB.objects.values("objecta__name")
        self.assertIn(" INNER JOIN ", str(qs.query))

    def test_ticket_21376(self):
        a = ObjectA.objects.create()
        ObjectC.objects.create(objecta=a)
        qs = ObjectC.objects.filter(
            Q(objecta=a) | Q(objectb__objecta=a),
        )
        qs = qs.filter(
            Q(objectb=1) | Q(objecta=a),
        )
        self.assertEqual(qs.count(), 1)
        tblname = connection.ops.quote_name(ObjectB._meta.db_table)
        self.assertIn(" LEFT OUTER JOIN %s" % tblname, str(qs.query))


class ForeignKeyToBaseExcludeTests(TestCase):
    def test_ticket_21787(self):
        sc1 = SpecialCategory.objects.create(special_name="sc1", name="sc1")
        sc2 = SpecialCategory.objects.create(special_name="sc2", name="sc2")
        sc3 = SpecialCategory.objects.create(special_name="sc3", name="sc3")
        c1 = CategoryItem.objects.create(category=sc1)
        CategoryItem.objects.create(category=sc2)
        self.assertSequenceEqual(
            SpecialCategory.objects.exclude(categoryitem__id=c1.pk).order_by("name"),
            [sc2, sc3],
        )
        self.assertSequenceEqual(
            SpecialCategory.objects.filter(categoryitem__id=c1.pk), [sc1]
        )


class ReverseM2MCustomPkTests(TestCase):
    def test_ticket_21879(self):
        cpt1 = CustomPkTag.objects.create(id="cpt1", tag="cpt1")
        cp1 = CustomPk.objects.create(name="cp1", extra="extra")
        cp1.custompktag_set.add(cpt1)
        self.assertSequenceEqual(CustomPk.objects.filter(custompktag=cpt1), [cp1])
        self.assertSequenceEqual(CustomPkTag.objects.filter(custom_pk=cp1), [cpt1])


class Ticket22429Tests(TestCase):
    def test_ticket_22429(self):
        sc1 = School.objects.create()
        st1 = Student.objects.create(school=sc1)

        sc2 = School.objects.create()
        st2 = Student.objects.create(school=sc2)

        cr = Classroom.objects.create(school=sc1)
        cr.students.add(st1)

        queryset = Student.objects.filter(~Q(classroom__school=F("school")))
        self.assertSequenceEqual(queryset, [st2])


class Ticket23605Tests(TestCase):
    def test_ticket_23605(self):
        # Test filtering on a complicated q-object from ticket's report.
        # The query structure is such that we have multiple nested subqueries.
        # The original problem was that the inner queries weren't relabeled
        # correctly.
        # See also #24090.
        a1 = Ticket23605A.objects.create()
        a2 = Ticket23605A.objects.create()
        c1 = Ticket23605C.objects.create(field_c0=10000.0)
        Ticket23605B.objects.create(
            field_b0=10000.0, field_b1=True, modelc_fk=c1, modela_fk=a1
        )
        complex_q = Q(
            pk__in=Ticket23605A.objects.filter(
                Q(
                    # True for a1 as field_b0 = 10000, field_c0=10000
                    # False for a2 as no ticket23605b found
                    ticket23605b__field_b0__gte=1000000
                    / F("ticket23605b__modelc_fk__field_c0")
                )
                &
                # True for a1 (field_b1=True)
                Q(ticket23605b__field_b1=True)
                & ~Q(
                    ticket23605b__pk__in=Ticket23605B.objects.filter(
                        ~(
                            # Same filters as above commented filters, but
                            # double-negated (one for Q() above, one for
                            # parentheses). So, again a1 match, a2 not.
                            Q(field_b1=True)
                            & Q(field_b0__gte=1000000 / F("modelc_fk__field_c0"))
                        )
                    )
                )
            ).filter(ticket23605b__field_b1=True)
        )
        qs1 = Ticket23605A.objects.filter(complex_q)
        self.assertSequenceEqual(qs1, [a1])
        qs2 = Ticket23605A.objects.exclude(complex_q)
        self.assertSequenceEqual(qs2, [a2])


class TestTicket24279(TestCase):
    def test_ticket_24278(self):
        School.objects.create()
        qs = School.objects.filter(Q(pk__in=()) | Q())
        self.assertSequenceEqual(qs, [])


class TestInvalidValuesRelation(SimpleTestCase):
    def test_invalid_values(self):
        msg = "Field 'id' expected a number but got 'abc'."
        with self.assertRaisesMessage(ValueError, msg):
            Annotation.objects.filter(tag="abc")
        with self.assertRaisesMessage(ValueError, msg):
            Annotation.objects.filter(tag__in=[123, "abc"])


class TestTicket24605(TestCase):
    def test_ticket_24605(self):
        """
        Subquery table names should be quoted.
        """
        i1 = Individual.objects.create(alive=True)
        RelatedIndividual.objects.create(related=i1)
        i2 = Individual.objects.create(alive=False)
        RelatedIndividual.objects.create(related=i2)
        i3 = Individual.objects.create(alive=True)
        i4 = Individual.objects.create(alive=False)

        self.assertSequenceEqual(
            Individual.objects.filter(
                Q(alive=False), Q(related_individual__isnull=True)
            ),
            [i4],
        )
        self.assertSequenceEqual(
            Individual.objects.exclude(
                Q(alive=False), Q(related_individual__isnull=True)
            ).order_by("pk"),
            [i1, i2, i3],
        )


class Ticket23622Tests(TestCase):
    @skipUnlessDBFeature("can_distinct_on_fields")
    def test_ticket_23622(self):
        """
        Make sure __pk__in and __in work the same for related fields when
        using a distinct on subquery.
        """
        a1 = Ticket23605A.objects.create()
        a2 = Ticket23605A.objects.create()
        c1 = Ticket23605C.objects.create(field_c0=0.0)
        Ticket23605B.objects.create(
            modela_fk=a1,
            field_b0=123,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a1,
            field_b0=23,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a1,
            field_b0=234,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a1,
            field_b0=12,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a2,
            field_b0=567,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a2,
            field_b0=76,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a2,
            field_b0=7,
            field_b1=True,
            modelc_fk=c1,
        )
        Ticket23605B.objects.create(
            modela_fk=a2,
            field_b0=56,
            field_b1=True,
            modelc_fk=c1,
        )
        qx = Q(
            ticket23605b__pk__in=Ticket23605B.objects.order_by(
                "modela_fk", "-field_b1"
            ).distinct("modela_fk")
        ) & Q(ticket23605b__field_b0__gte=300)
        qy = Q(
            ticket23605b__in=Ticket23605B.objects.order_by(
                "modela_fk", "-field_b1"
            ).distinct("modela_fk")
        ) & Q(ticket23605b__field_b0__gte=300)
        self.assertEqual(
            set(Ticket23605A.objects.filter(qx).values_list("pk", flat=True)),
            set(Ticket23605A.objects.filter(qy).values_list("pk", flat=True)),
        )
        self.assertSequenceEqual(Ticket23605A.objects.filter(qx), [a2])
