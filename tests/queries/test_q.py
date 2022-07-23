from django.core.exceptions import FieldError
from django.db.models import (
    BooleanField,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Value,
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Lower
from django.db.models.sql.where import NothingNode
from django.test import SimpleTestCase, TestCase

from .models import Tag


class QTests(SimpleTestCase):
    def test_combine_and_empty(self):
        q = Q(x=1)
        self.assertEqual(q & Q(), q)
        self.assertEqual(Q() & q, q)

        q = Q(x__in={}.keys())
        self.assertEqual(q & Q(), q)
        self.assertEqual(Q() & q, q)

    def test_combine_and_both_empty(self):
        self.assertEqual(Q() & Q(), Q())

    def test_combine_or_empty(self):
        q = Q(x=1)
        self.assertEqual(q | Q(), q)
        self.assertEqual(Q() | q, q)

        q = Q(x__in={}.keys())
        self.assertEqual(q | Q(), q)
        self.assertEqual(Q() | q, q)

    def test_combine_xor_empty(self):
        q = Q(x=1)
        self.assertEqual(q ^ Q(), q)
        self.assertEqual(Q() ^ q, q)

        q = Q(x__in={}.keys())
        self.assertEqual(q ^ Q(), q)
        self.assertEqual(Q() ^ q, q)

    def test_combine_empty_copy(self):
        base_q = Q(x=1)
        tests = [
            base_q | Q(),
            Q() | base_q,
            base_q & Q(),
            Q() & base_q,
            base_q ^ Q(),
            Q() ^ base_q,
        ]
        for i, q in enumerate(tests):
            with self.subTest(i=i):
                self.assertEqual(q, base_q)
                self.assertIsNot(q, base_q)

    def test_combine_or_both_empty(self):
        self.assertEqual(Q() | Q(), Q())

    def test_combine_xor_both_empty(self):
        self.assertEqual(Q() ^ Q(), Q())

    def test_combine_not_q_object(self):
        obj = object()
        q = Q(x=1)
        with self.assertRaisesMessage(TypeError, str(obj)):
            q | obj
        with self.assertRaisesMessage(TypeError, str(obj)):
            q & obj
        with self.assertRaisesMessage(TypeError, str(obj)):
            q ^ obj

    def test_combine_negated_boolean_expression(self):
        tagged = Tag.objects.filter(category=OuterRef("pk"))
        tests = [
            Q() & ~Exists(tagged),
            Q() | ~Exists(tagged),
            Q() ^ ~Exists(tagged),
        ]
        for q in tests:
            with self.subTest(q=q):
                self.assertIs(q.negated, True)

    def test_deconstruct(self):
        q = Q(price__gt=F("discounted_price"))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(path, "django.db.models.Q")
        self.assertEqual(args, (("price__gt", F("discounted_price")),))
        self.assertEqual(kwargs, {})

    def test_deconstruct_negated(self):
        q = ~Q(price__gt=F("discounted_price"))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (("price__gt", F("discounted_price")),))
        self.assertEqual(kwargs, {"_negated": True})

    def test_deconstruct_or(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 | q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(
            args,
            (
                ("price__gt", F("discounted_price")),
                ("price", F("discounted_price")),
            ),
        )
        self.assertEqual(kwargs, {"_connector": Q.OR})

    def test_deconstruct_xor(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 ^ q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(
            args,
            (
                ("price__gt", F("discounted_price")),
                ("price", F("discounted_price")),
            ),
        )
        self.assertEqual(kwargs, {"_connector": Q.XOR})

    def test_deconstruct_and(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 & q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(
            args,
            (
                ("price__gt", F("discounted_price")),
                ("price", F("discounted_price")),
            ),
        )
        self.assertEqual(kwargs, {})

    def test_deconstruct_multiple_kwargs(self):
        q = Q(price__gt=F("discounted_price"), price=F("discounted_price"))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(
            args,
            (
                ("price", F("discounted_price")),
                ("price__gt", F("discounted_price")),
            ),
        )
        self.assertEqual(kwargs, {})

    def test_deconstruct_nested(self):
        q = Q(Q(price__gt=F("discounted_price")))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (Q(price__gt=F("discounted_price")),))
        self.assertEqual(kwargs, {})

    def test_deconstruct_boolean_expression(self):
        expr = RawSQL("1 = 1", BooleanField())
        q = Q(expr)
        _, args, kwargs = q.deconstruct()
        self.assertEqual(args, (expr,))
        self.assertEqual(kwargs, {})

    def test_reconstruct(self):
        q = Q(price__gt=F("discounted_price"))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_negated(self):
        q = ~Q(price__gt=F("discounted_price"))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_or(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 | q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_xor(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 ^ q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_and(self):
        q1 = Q(price__gt=F("discounted_price"))
        q2 = Q(price=F("discounted_price"))
        q = q1 & q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_flatten(self):
        q = Q()
        self.assertEqual(list(q.flatten()), [q])
        q = Q(NothingNode())
        self.assertEqual(list(q.flatten()), [q, q.children[0]])
        q = Q(
            ExpressionWrapper(
                Q(RawSQL("id = 0", params=(), output_field=BooleanField()))
                | Q(price=Value("4.55"))
                | Q(name=Lower("category")),
                output_field=BooleanField(),
            )
        )
        flatten = list(q.flatten())
        self.assertEqual(len(flatten), 7)


class QCheckTests(TestCase):
    def test_basic(self):
        q = Q(price__gt=20)
        self.assertIs(q.check({"price": 30}), True)
        self.assertIs(q.check({"price": 10}), False)

    def test_expression(self):
        q = Q(name="test")
        self.assertIs(q.check({"name": Lower(Value("TeSt"))}), True)
        self.assertIs(q.check({"name": Value("other")}), False)

    def test_missing_field(self):
        q = Q(description__startswith="prefix")
        msg = "Cannot resolve keyword 'description' into field."
        with self.assertRaisesMessage(FieldError, msg):
            q.check({"name": "test"})

    def test_boolean_expression(self):
        q = Q(ExpressionWrapper(Q(price__gt=20), output_field=BooleanField()))
        self.assertIs(q.check({"price": 25}), True)
        self.assertIs(q.check({"price": Value(10)}), False)

    def test_rawsql(self):
        """
        RawSQL expressions cause a database error because "price" cannot be
        replaced by its value. In this case, Q.check() logs a warning and
        return True.
        """
        q = Q(RawSQL("price > %s", params=(20,), output_field=BooleanField()))
        with self.assertLogs("django.db.models", "WARNING") as cm:
            self.assertIs(q.check({"price": 10}), True)
        self.assertIn(
            f"Got a database error calling check() on {q!r}: ",
            cm.records[0].getMessage(),
        )
