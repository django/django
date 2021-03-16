from django.db.models import Exists, F, OuterRef, Q
from django.test import SimpleTestCase

from .models import Tag


class QTests(SimpleTestCase):
    def test_all_empty(self):
        q = Q.all({}.keys())
        self.assertEqual(q, Q.TRUE)

        q = Q.all([Q(), Q()])
        self.assertEqual(q, Q.TRUE)

    def test_all(self):
        q = Q.all([Q(x=1), Q()])
        self.assertEqual(q, Q(x=1))

        q = Q.all([Q(x__gt=1, x__lt=5), Q(x=7)])
        self.assertEqual(q, Q(x__gt=1, x__lt=5) & Q(x=7))

    def test_any_empty(self):
        q = Q.any({}.keys())
        self.assertEqual(q, Q.FALSE)

        q = Q.any([Q(), Q()])
        self.assertEqual(q, Q.FALSE)

    def test_any(self):
        q = Q.any([Q(x=1), Q()])
        self.assertEqual(q, Q(x=1))

        q = Q.any([Q(x__gt=1, x__lt=5), Q(x=7)])
        self.assertEqual(q, Q(x__gt=1, x__lt=5) | Q(x=7))

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

    def test_combine_or_both_empty(self):
        self.assertEqual(Q() | Q(), Q())

    def test_combine_nested_empty(self):
        q = Q(x=1)
        self.assertEqual(q | Q(Q()), q)
        self.assertEqual(Q(Q()) | q, q)
        self.assertEqual(q & Q(Q()), q)
        self.assertEqual(Q(Q()) & q, q)

        q = Q(Q()) | Q(Q())
        self.assertIs(q.empty(), True)

        q = Q(Q()) & Q(Q())
        self.assertIs(q.empty(), True)

    def test_combine_not_q_object(self):
        obj = object()
        q = Q(x=1)
        with self.assertRaisesMessage(TypeError, str(obj)):
            q | obj
        with self.assertRaisesMessage(TypeError, str(obj)):
            q & obj

    def test_deconstruct(self):
        q = Q(price__gt=F('discounted_price'))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(path, 'django.db.models.Q')
        self.assertEqual(args, (('price__gt', F('discounted_price')),))
        self.assertEqual(kwargs, {})

    def test_deconstruct_negated(self):
        q = ~Q(price__gt=F('discounted_price'))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (('price__gt', F('discounted_price')),))
        self.assertEqual(kwargs, {'_negated': True})

    def test_deconstruct_or(self):
        q1 = Q(price__gt=F('discounted_price'))
        q2 = Q(price=F('discounted_price'))
        q = q1 | q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (
            ('price__gt', F('discounted_price')),
            ('price', F('discounted_price')),
        ))
        self.assertEqual(kwargs, {'_connector': 'OR'})

    def test_deconstruct_and(self):
        q1 = Q(price__gt=F('discounted_price'))
        q2 = Q(price=F('discounted_price'))
        q = q1 & q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (
            ('price__gt', F('discounted_price')),
            ('price', F('discounted_price')),
        ))
        self.assertEqual(kwargs, {})

    def test_deconstruct_multiple_kwargs(self):
        q = Q(price__gt=F('discounted_price'), price=F('discounted_price'))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (
            ('price', F('discounted_price')),
            ('price__gt', F('discounted_price')),
        ))
        self.assertEqual(kwargs, {})

    def test_deconstruct_nested(self):
        q = Q(Q(price__gt=F('discounted_price')))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (Q(price__gt=F('discounted_price')),))
        self.assertEqual(kwargs, {})

    def test_deconstruct_boolean_expression(self):
        tagged = Tag.objects.filter(category=OuterRef('pk'))
        q = Q(Exists(tagged))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(args, (Exists(tagged),))
        self.assertEqual(kwargs, {})

    def test_empty(self):
        q = Q()
        self.assertIs(q.empty(), True)

        q = Q(Q(), ~Q(), Q(Q()))
        self.assertIs(q.empty(), True)

        q = Q(x=1)
        self.assertIs(q.empty(), False)

        q = Q(Q(), ~Q(), Q(Q(x=1)))
        self.assertIs(q.empty(), False)

    def test_reconstruct(self):
        q = Q(price__gt=F('discounted_price'))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_negated(self):
        q = ~Q(price__gt=F('discounted_price'))
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_or(self):
        q1 = Q(price__gt=F('discounted_price'))
        q2 = Q(price=F('discounted_price'))
        q = q1 | q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)

    def test_reconstruct_and(self):
        q1 = Q(price__gt=F('discounted_price'))
        q2 = Q(price=F('discounted_price'))
        q = q1 & q2
        path, args, kwargs = q.deconstruct()
        self.assertEqual(Q(*args, **kwargs), q)
