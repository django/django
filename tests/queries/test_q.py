from django.db.models import BooleanField, Exists, F, OuterRef, Q
from django.db.models.expressions import RawSQL
from django.test import SimpleTestCase

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

    def test_combine_empty_copy(self):
        base_q = Q(x=1)
        tests = [
            base_q | Q(),
            Q() | base_q,
            base_q & Q(),
            Q() & base_q,
        ]
        for i, q in enumerate(tests):
            with self.subTest(i=i):
                self.assertEqual(q, base_q)
                self.assertIsNot(q, base_q)

    def test_combine_or_both_empty(self):
        self.assertEqual(Q() | Q(), Q())

    def test_combine_not_q_object(self):
        obj = object()
        q = Q(x=1)
        with self.assertRaisesMessage(TypeError, str(obj)):
            q | obj
        with self.assertRaisesMessage(TypeError, str(obj)):
            q & obj

    def test_combine_negated_boolean_expression(self):
        tagged = Tag.objects.filter(category=OuterRef('pk'))
        tests = [
            Q() & ~Exists(tagged),
            Q() | ~Exists(tagged),
        ]
        for q in tests:
            with self.subTest(q=q):
                self.assertIs(q.negated, True)

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
        expr = RawSQL('1 = 1', BooleanField())
        q = Q(expr)
        _, args, kwargs = q.deconstruct()
        self.assertEqual(args, (expr,))
        self.assertEqual(kwargs, {})

    def test_jsonify(self):
        q = Q(price__gt=50)
        correct_out = {
            'AND': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': False
                }
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_many_subqueries_or(self):
        q = (
            Q(price__gt=50) |
            Q(price__gt=60) |
            Q(price__gt=70) |
            Q(price__gt=80) |
            Q(price__gt=90) |
            Q(price__gt=100)
        )
        correct_out = {
            'OR': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': False
                },
                1: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 60,
                    'include_null': True,
                    'not': False
                },
                2: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 70,
                    'include_null': True,
                    'not': False
                },
                3: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 80,
                    'include_null': True,
                    'not': False
                },
                4: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 90,
                    'include_null': True,
                    'not': False
                },
                5: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 100,
                    'include_null': True,
                    'not': False
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_many_subqueries_and(self):
        q = (
            Q(price__gt=50) &
            Q(price__gt=60) &
            Q(price__gt=70) &
            Q(price__gt=80) &
            Q(price__gt=90) &
            Q(price__gt=100)
        )
        correct_out = {
            'AND': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': False
                },
                1: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 60,
                    'include_null': True,
                    'not': False
                },
                2: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 70,
                    'include_null': True,
                    'not': False
                },
                3: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 80,
                    'include_null': True,
                    'not': False
                },
                4: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 90,
                    'include_null': True,
                    'not': False
                },
                5: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 100,
                    'include_null': True,
                    'not': False
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_negated(self):
        q = ~Q(price__gt=50)
        correct_out = {
            'AND': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': True
                }
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_or(self):
        q1 = Q(price__gt=50)
        q2 = Q(discount=75)
        q = q1 | q2
        correct_out = {
            'OR': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': False
                },
                1: {
                    'field_of_interest': 'discount',
                    'comparison_phrase': 'eq',
                    'comparison_value': 75,
                    'include_null': True,
                    'not': False
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_and(self):
        q1 = Q(price__gte=50)
        q2 = Q(account_balance__lt=500)
        q = ~q1 & q2
        correct_out = {
            'AND': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gte',
                    'comparison_value': 50,
                    'include_null': True,
                    'not': True
                },
                1: {
                    'field_of_interest': 'account_balance',
                    'comparison_phrase': 'lt',
                    'comparison_value': 500,
                    'include_null': True,
                    'not': False
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_filter_dict(self):
        filter_dict = {
            'name__icontains': 'Josh',
            'balance__gte': 7000,
            'location__contains': 'charlotte'
        }
        q = Q(**filter_dict)
        correct_out = {
            # Note: order is alphabetized by field.
            'AND': {
                0: {
                    'field_of_interest': 'balance',
                    'comparison_phrase': 'gte',
                    'comparison_value': 7000,
                    'include_null': True,
                    'not': False
                },
                1: {
                    'field_of_interest': 'location',
                    'comparison_phrase': 'contains',
                    'comparison_value': 'charlotte',
                    'include_null': True,
                    'not': False
                },
                2: {
                    'field_of_interest': 'name',
                    'comparison_phrase': 'icontains',
                    'comparison_value': 'Josh',
                    'include_null': True,
                    'not': False
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_negate_filter_dict(self):
        filter_dict = {
            'name__icontains': 'Josh',
            'balance__gte': 7000,
            'location__contains': 'charlotte'
        }
        q = ~Q(**filter_dict)
        correct_out = {
            # Note: order is alphabetized by field.
            'AND': {
                0: {
                    'field_of_interest': 'balance',
                    'comparison_phrase': 'gte',
                    'comparison_value': 7000,
                    'include_null': True,
                    'not': True
                },
                1: {
                    'field_of_interest': 'location',
                    'comparison_phrase': 'contains',
                    'comparison_value': 'charlotte',
                    'include_null': True,
                    'not': True
                },
                2: {
                    'field_of_interest': 'name',
                    'comparison_phrase': 'icontains',
                    'comparison_value': 'Josh',
                    'include_null': True,
                    'not': True
                },
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_multiple_operators(self):
        q1 = Q(price__gt=10)
        q2 = Q(product_type__eq='fruit')
        q3 = Q(product_type__eq='vegetable')
        q = ~q1 & (q2 | q3)
        correct_out = {
            # Note: order is alphabetized by field.
            'AND': {
                0: {
                    'field_of_interest': 'price',
                    'comparison_phrase': 'gt',
                    'comparison_value': 10,
                    'include_null': True,
                    'not': True
                },
                1: {
                    'OR': {
                        0: {
                            'field_of_interest': 'product_type',
                            'comparison_phrase': 'eq',
                            'comparison_value': 'fruit',
                            'include_null': True,
                            'not': False
                        },
                        1: {
                            'field_of_interest': 'product_type',
                            'comparison_phrase': 'eq',
                            'comparison_value': 'vegetable',
                            'include_null': True,
                            'not': False
                        }
                    }
                }
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_nested(self):
        q1 = Q(price__gt=10)
        q2 = Q(product_type__eq='fruit')
        q3 = Q(product_type__eq='vegetable')
        # This will add an extra 'AND' outer key.
        q = Q(~q1 & (q2 | q3))
        correct_out = {
            # Note: order is alphabetized by field.
            'AND': {
                0: {
                    'AND': {
                        0: {
                            'field_of_interest': 'price',
                            'comparison_phrase': 'gt',
                            'comparison_value': 10,
                            'include_null': True,
                            'not': True
                        },
                        1: {
                            'OR': {
                                0: {
                                    'field_of_interest': 'product_type',
                                    'comparison_phrase': 'eq',
                                    'comparison_value': 'fruit',
                                    'include_null': True,
                                    'not': False
                                },
                                1: {
                                    'field_of_interest': 'product_type',
                                    'comparison_phrase': 'eq',
                                    'comparison_value': 'vegetable',
                                    'include_null': True,
                                    'not': False
                                }
                            }
                        }
                    }
                }
            }
        }
        json_out = q.jsonify()
        self.assertEqual(json_out, correct_out)

    def test_jsonify_complex(self):
        q1 = Q(city__icontains='Chicago')
        q2 = Q(ask__lte=50)
        q3 = Q(city__icontains='San Fran')
        q4 = Q(ask__lte=20)
        q = q3 | ~q4 | (q1 & q2)
        correct_out = {
            'OR': {
                0: {
                    'field_of_interest': 'city',
                    'comparison_phrase': 'icontains',
                    'comparison_value': 'San Fran',
                    'not': False,
                    'include_null': True
                },
                1: {
                    'field_of_interest': 'ask',
                    'comparison_phrase': 'lte',
                    'comparison_value': 20,
                    'not': True,
                    'include_null': True
                },
                2: {
                    'AND': {
                        0: {
                            'field_of_interest': 'city',
                            'comparison_phrase': 'icontains',
                            'comparison_value': 'Chicago',
                            'not': False,
                            'include_null': True
                        },
                        1: {
                            'field_of_interest': 'ask',
                            'comparison_phrase': 'lte',
                            'comparison_value': 50,
                            'not': False,
                            'include_null': True
                        }
                    }
                }
            }
        }
        json_out = q.jsonify()
        self.assertEqual(correct_out, json_out)

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
