from __future__ import unicode_literals

from copy import deepcopy
import datetime

from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import F
from django.db import transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import Approximate
from django.utils import six

from .models import Company, Employee, Number, Experiment


class ExpressionsTests(TestCase):

    def test_filter(self):
        Company.objects.create(
            name="Example Inc.", num_employees=2300, num_chairs=5,
            ceo=Employee.objects.create(firstname="Joe", lastname="Smith")
        )
        Company.objects.create(
            name="Foobar Ltd.", num_employees=3, num_chairs=4,
            ceo=Employee.objects.create(firstname="Frank", lastname="Meyer")
        )
        Company.objects.create(
            name="Test GmbH", num_employees=32, num_chairs=1,
            ceo=Employee.objects.create(firstname="Max", lastname="Mustermann")
        )

        company_query = Company.objects.values(
            "name", "num_employees", "num_chairs"
        ).order_by(
            "name", "num_employees", "num_chairs"
        )

        # We can filter for companies where the number of employees is greater
        # than the number of chairs.
        self.assertQuerysetEqual(
            company_query.filter(num_employees__gt=F("num_chairs")), [
                {
                    "num_chairs": 5,
                    "name": "Example Inc.",
                    "num_employees": 2300,
                },
                {
                    "num_chairs": 1,
                    "name": "Test GmbH",
                    "num_employees": 32
                },
            ],
            lambda o: o
        )

        # We can set one field to have the value of another field
        # Make sure we have enough chairs
        company_query.update(num_chairs=F("num_employees"))
        self.assertQuerysetEqual(
            company_query, [
                {
                    "num_chairs": 2300,
                    "name": "Example Inc.",
                    "num_employees": 2300
                },
                {
                    "num_chairs": 3,
                    "name": "Foobar Ltd.",
                    "num_employees": 3
                },
                {
                    "num_chairs": 32,
                    "name": "Test GmbH",
                    "num_employees": 32
                }
            ],
            lambda o: o
        )

        # We can perform arithmetic operations in expressions
        # Make sure we have 2 spare chairs
        company_query.update(num_chairs=F("num_employees") + 2)
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 2302,
                    'name': 'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 5,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 34,
                    'name': 'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # Law of order of operations is followed
        company_query.update(
            num_chairs=F('num_employees') + 2 * F('num_employees')
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 6900,
                    'name': 'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 9,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 96,
                    'name': 'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # Law of order of operations can be overridden by parentheses
        company_query.update(
            num_chairs=((F('num_employees') + 2) * F('num_employees'))
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 5294600,
                    'name': 'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 15,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 1088,
                    'name': 'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # The relation of a foreign key can become copied over to an other
        # foreign key.
        self.assertEqual(
            Company.objects.update(point_of_contact=F('ceo')),
            3
        )
        self.assertQuerysetEqual(
            Company.objects.all(), [
                "Joe Smith",
                "Frank Meyer",
                "Max Mustermann",
            ],
            lambda c: six.text_type(c.point_of_contact),
            ordered=False
        )

        c = Company.objects.all()[0]
        c.point_of_contact = Employee.objects.create(firstname="Guido", lastname="van Rossum")
        c.save()

        # F Expressions can also span joins
        self.assertQuerysetEqual(
            Company.objects.filter(ceo__firstname=F("point_of_contact__firstname")), [
                "Foobar Ltd.",
                "Test GmbH",
            ],
            lambda c: c.name,
            ordered=False
        )

        Company.objects.exclude(
            ceo__firstname=F("point_of_contact__firstname")
        ).update(name="foo")
        self.assertEqual(
            Company.objects.exclude(
                ceo__firstname=F('point_of_contact__firstname')
            ).get().name,
            "foo",
        )

        with transaction.atomic():
            with self.assertRaises(FieldError):
                Company.objects.exclude(
                    ceo__firstname=F('point_of_contact__firstname')
                ).update(name=F('point_of_contact__lastname'))

        # F expressions can be used to update attributes on single objects
        test_gmbh = Company.objects.get(name="Test GmbH")
        self.assertEqual(test_gmbh.num_employees, 32)
        test_gmbh.num_employees = F("num_employees") + 4
        test_gmbh.save()
        test_gmbh = Company.objects.get(pk=test_gmbh.pk)
        self.assertEqual(test_gmbh.num_employees, 36)

        # F expressions cannot be used to update attributes which are foreign
        # keys, or attributes which involve joins.
        test_gmbh.point_of_contact = None
        test_gmbh.save()
        self.assertIsNone(test_gmbh.point_of_contact)

        def test():
            test_gmbh.point_of_contact = F("ceo")
        self.assertRaises(ValueError, test)

        test_gmbh.point_of_contact = test_gmbh.ceo
        test_gmbh.save()
        test_gmbh.name = F("ceo__last_name")
        self.assertRaises(FieldError, test_gmbh.save)

        # F expressions cannot be used to update attributes on objects which do
        # not yet exist in the database
        acme = Company(
            name="The Acme Widget Co.", num_employees=12, num_chairs=5,
            ceo=test_gmbh.ceo
        )
        acme.num_employees = F("num_employees") + 16
        self.assertRaises(TypeError, acme.save)

    def test_ticket_11722_iexact_lookup(self):
        Employee.objects.create(firstname="John", lastname="Doe")
        Employee.objects.create(firstname="Test", lastname="test")

        queryset = Employee.objects.filter(firstname__iexact=F('lastname'))
        self.assertQuerysetEqual(queryset, ["<Employee: Test test>"])

    @skipIfDBFeature('has_case_insensitive_like')
    def test_ticket_16731_startswith_lookup(self):
        Employee.objects.create(firstname="John", lastname="Doe")
        e2 = Employee.objects.create(firstname="Jack", lastname="Jackson")
        e3 = Employee.objects.create(firstname="Jack", lastname="jackson")
        self.assertQuerysetEqual(
            Employee.objects.filter(lastname__startswith=F('firstname')),
            [e2], lambda x: x)
        self.assertQuerysetEqual(
            Employee.objects.filter(lastname__istartswith=F('firstname')).order_by('pk'),
            [e2, e3], lambda x: x)

    def test_ticket_18375_join_reuse(self):
        # Test that reverse multijoin F() references and the lookup target
        # the same join. Pre #18375 the F() join was generated first, and the
        # lookup couldn't reuse that join.
        qs = Employee.objects.filter(
            company_ceo_set__num_chairs=F('company_ceo_set__num_employees'))
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_ticket_18375_kwarg_ordering(self):
        # The next query was dict-randomization dependent - if the "gte=1"
        # was seen first, then the F() will reuse the join generated by the
        # gte lookup, if F() was seen first, then it generated a join the
        # other lookups could not reuse.
        qs = Employee.objects.filter(
            company_ceo_set__num_chairs=F('company_ceo_set__num_employees'),
            company_ceo_set__num_chairs__gte=1)
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_ticket_18375_kwarg_ordering_2(self):
        # Another similar case for F() than above. Now we have the same join
        # in two filter kwargs, one in the lhs lookup, one in F. Here pre
        # #18375 the amount of joins generated was random if dict
        # randomization was enabled, that is the generated query dependent
        # on which clause was seen first.
        qs = Employee.objects.filter(
            company_ceo_set__num_employees=F('pk'),
            pk=F('company_ceo_set__num_employees')
        )
        self.assertEqual(str(qs.query).count('JOIN'), 1)

    def test_ticket_18375_chained_filters(self):
        # Test that F() expressions do not reuse joins from previous filter.
        qs = Employee.objects.filter(
            company_ceo_set__num_employees=F('pk')
        ).filter(
            company_ceo_set__num_employees=F('company_ceo_set__num_employees')
        )
        self.assertEqual(str(qs.query).count('JOIN'), 2)

    def test_F_object_deepcopy(self):
        """
        Make sure F objects can be deepcopied (#23492)
        """
        f = F("foo")
        g = deepcopy(f)
        self.assertEqual(f.name, g.name)


class ExpressionsNumericTests(TestCase):

    def setUp(self):
        Number(integer=-1).save()
        Number(integer=42).save()
        Number(integer=1337).save()
        self.assertEqual(Number.objects.update(float=F('integer')), 3)

    def test_fill_with_value_from_same_object(self):
        """
        We can fill a value in all objects with an other value of the
        same object.
        """
        self.assertQuerysetEqual(
            Number.objects.all(),
            [
                '<Number: -1, -1.000>',
                '<Number: 42, 42.000>',
                '<Number: 1337, 1337.000>'
            ],
            ordered=False
        )

    def test_increment_value(self):
        """
        We can increment a value of all objects in a query set.
        """
        self.assertEqual(
            Number.objects.filter(integer__gt=0)
                  .update(integer=F('integer') + 1),
            2)

        self.assertQuerysetEqual(
            Number.objects.all(),
            [
                '<Number: -1, -1.000>',
                '<Number: 43, 42.000>',
                '<Number: 1338, 1337.000>'
            ],
            ordered=False
        )

    def test_filter_not_equals_other_field(self):
        """
        We can filter for objects, where a value is not equals the value
        of an other field.
        """
        self.assertEqual(
            Number.objects.filter(integer__gt=0)
                  .update(integer=F('integer') + 1),
            2)
        self.assertQuerysetEqual(
            Number.objects.exclude(float=F('integer')),
            [
                '<Number: 43, 42.000>',
                '<Number: 1338, 1337.000>'
            ],
            ordered=False
        )

    def test_complex_expressions(self):
        """
        Complex expressions of different connection types are possible.
        """
        n = Number.objects.create(integer=10, float=123.45)
        self.assertEqual(Number.objects.filter(pk=n.pk)
            .update(float=F('integer') + F('float') * 2), 1)

        self.assertEqual(Number.objects.get(pk=n.pk).integer, 10)
        self.assertEqual(Number.objects.get(pk=n.pk).float, Approximate(256.900, places=3))


class ExpressionOperatorTests(TestCase):
    def setUp(self):
        self.n = Number.objects.create(integer=42, float=15.5)

    def test_lefthand_addition(self):
        # LH Addition of floats and integers
        Number.objects.filter(pk=self.n.pk).update(
            integer=F('integer') + 15,
            float=F('float') + 42.7
        )

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 57)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(58.200, places=3))

    def test_lefthand_subtraction(self):
        # LH Subtraction of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') - 15,
                                              float=F('float') - 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(-27.200, places=3))

    def test_lefthand_multiplication(self):
        # Multiplication of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') * 15,
                                              float=F('float') * 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 630)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(661.850, places=3))

    def test_lefthand_division(self):
        # LH Division of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') / 2,
                                              float=F('float') / 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 21)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(0.363, places=3))

    def test_lefthand_modulo(self):
        # LH Modulo arithmetic on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') % 20)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 2)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_lefthand_bitwise_and(self):
        # LH Bitwise ands on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer').bitand(56))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 40)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    @skipUnlessDBFeature('supports_bitwise_or')
    def test_lefthand_bitwise_or(self):
        # LH Bitwise or on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer').bitor(48))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 58)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_lefthand_power(self):
        # LH Powert arithmetic operation on floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') ** 2,
                                                float=F('float') ** 1.5)
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 1764)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(61.02, places=2))

    def test_right_hand_addition(self):
        # Right hand operators
        Number.objects.filter(pk=self.n.pk).update(integer=15 + F('integer'),
                                              float=42.7 + F('float'))

        # RH Addition of floats and integers
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 57)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(58.200, places=3))

    def test_right_hand_subtraction(self):
        Number.objects.filter(pk=self.n.pk).update(integer=15 - F('integer'),
                                              float=42.7 - F('float'))

        # RH Subtraction of floats and integers
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, -27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(27.200, places=3))

    def test_right_hand_multiplication(self):
        # RH Multiplication of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=15 * F('integer'),
                                              float=42.7 * F('float'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 630)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(661.850, places=3))

    def test_right_hand_division(self):
        # RH Division of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=640 / F('integer'),
                                              float=42.7 / F('float'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 15)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(2.755, places=3))

    def test_right_hand_modulo(self):
        # RH Modulo arithmetic on integers
        Number.objects.filter(pk=self.n.pk).update(integer=69 % F('integer'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_righthand_power(self):
        # RH Powert arithmetic operation on floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=2 ** F('integer'),
                                                float=1.5 ** F('float'))
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 4398046511104)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(536.308, places=3))


class FTimeDeltaTests(TestCase):

    def setUp(self):
        sday = datetime.date(2010, 6, 25)
        stime = datetime.datetime(2010, 6, 25, 12, 15, 30, 747000)
        midnight = datetime.time(0)

        delta0 = datetime.timedelta(0)
        delta1 = datetime.timedelta(microseconds=253000)
        delta2 = datetime.timedelta(seconds=44)
        delta3 = datetime.timedelta(hours=21, minutes=8)
        delta4 = datetime.timedelta(days=10)

        # Test data is set so that deltas and delays will be
        # strictly increasing.
        self.deltas = []
        self.delays = []
        self.days_long = []

        # e0: started same day as assigned, zero duration
        end = stime + delta0
        e0 = Experiment.objects.create(name='e0', assigned=sday, start=stime,
            end=end, completed=end.date())
        self.deltas.append(delta0)
        self.delays.append(e0.start -
            datetime.datetime.combine(e0.assigned, midnight))
        self.days_long.append(e0.completed - e0.assigned)

        # e1: started one day after assigned, tiny duration, data
        # set so that end time has no fractional seconds, which
        # tests an edge case on sqlite. This Experiment is only
        # included in the test data when the DB supports microsecond
        # precision.
        if connection.features.supports_microsecond_precision:
            delay = datetime.timedelta(1)
            end = stime + delay + delta1
            e1 = Experiment.objects.create(name='e1', assigned=sday,
                start=stime + delay, end=end, completed=end.date())
            self.deltas.append(delta1)
            self.delays.append(e1.start -
                datetime.datetime.combine(e1.assigned, midnight))
            self.days_long.append(e1.completed - e1.assigned)

        # e2: started three days after assigned, small duration
        end = stime + delta2
        e2 = Experiment.objects.create(name='e2',
            assigned=sday - datetime.timedelta(3), start=stime, end=end,
            completed=end.date())
        self.deltas.append(delta2)
        self.delays.append(e2.start -
            datetime.datetime.combine(e2.assigned, midnight))
        self.days_long.append(e2.completed - e2.assigned)

        # e3: started four days after assigned, medium duration
        delay = datetime.timedelta(4)
        end = stime + delay + delta3
        e3 = Experiment.objects.create(name='e3',
            assigned=sday, start=stime + delay, end=end, completed=end.date())
        self.deltas.append(delta3)
        self.delays.append(e3.start -
            datetime.datetime.combine(e3.assigned, midnight))
        self.days_long.append(e3.completed - e3.assigned)

        # e4: started 10 days after assignment, long duration
        end = stime + delta4
        e4 = Experiment.objects.create(name='e4',
            assigned=sday - datetime.timedelta(10), start=stime, end=end,
            completed=end.date())
        self.deltas.append(delta4)
        self.delays.append(e4.start -
            datetime.datetime.combine(e4.assigned, midnight))
        self.days_long.append(e4.completed - e4.assigned)
        self.expnames = [e.name for e in Experiment.objects.all()]

    def test_multiple_query_compilation(self):
        # Ticket #21643
        queryset = Experiment.objects.filter(end__lt=F('start') + datetime.timedelta(hours=1))
        q1 = str(queryset.query)
        q2 = str(queryset.query)
        self.assertEqual(q1, q2)

    def test_query_clone(self):
        # Ticket #21643
        qs = Experiment.objects.filter(end__lt=F('start') + datetime.timedelta(hours=1))
        qs2 = qs.all()
        list(qs)
        list(qs2)

    def test_delta_add(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            test_set = [e.name for e in
                Experiment.objects.filter(end__lt=F('start') + delta)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(end__lte=F('start') + delta)]
            self.assertEqual(test_set, self.expnames[:i + 1])

    def test_delta_subtract(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            test_set = [e.name for e in
                Experiment.objects.filter(start__gt=F('end') - delta)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(start__gte=F('end') - delta)]
            self.assertEqual(test_set, self.expnames[:i + 1])

    def test_exclude(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            test_set = [e.name for e in
                Experiment.objects.exclude(end__lt=F('start') + delta)]
            self.assertEqual(test_set, self.expnames[i:])

            test_set = [e.name for e in
                Experiment.objects.exclude(end__lte=F('start') + delta)]
            self.assertEqual(test_set, self.expnames[i + 1:])

    def test_date_comparison(self):
        for i in range(len(self.days_long)):
            days = self.days_long[i]
            test_set = [e.name for e in
                Experiment.objects.filter(completed__lt=F('assigned') + days)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(completed__lte=F('assigned') + days)]
            self.assertEqual(test_set, self.expnames[:i + 1])

    @skipUnlessDBFeature("supports_mixed_date_datetime_comparisons")
    def test_mixed_comparisons1(self):
        for i in range(len(self.delays)):
            delay = self.delays[i]
            if not connection.features.supports_microsecond_precision:
                delay = datetime.timedelta(delay.days, delay.seconds)
            test_set = [e.name for e in
                Experiment.objects.filter(assigned__gt=F('start') - delay)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(assigned__gte=F('start') - delay)]
            self.assertEqual(test_set, self.expnames[:i + 1])

    def test_mixed_comparisons2(self):
        delays = [datetime.timedelta(delay.days) for delay in self.delays]
        for i in range(len(delays)):
            delay = delays[i]
            test_set = [e.name for e in
                Experiment.objects.filter(start__lt=F('assigned') + delay)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(start__lte=F('assigned') + delay +
                    datetime.timedelta(1))]
            self.assertEqual(test_set, self.expnames[:i + 1])

    def test_delta_update(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            exps = Experiment.objects.all()
            expected_durations = [e.duration() for e in exps]
            expected_starts = [e.start + delta for e in exps]
            expected_ends = [e.end + delta for e in exps]

            Experiment.objects.update(start=F('start') + delta, end=F('end') + delta)
            exps = Experiment.objects.all()
            new_starts = [e.start for e in exps]
            new_ends = [e.end for e in exps]
            new_durations = [e.duration() for e in exps]
            self.assertEqual(expected_starts, new_starts)
            self.assertEqual(expected_ends, new_ends)
            self.assertEqual(expected_durations, new_durations)

    def test_delta_invalid_op_mult(self):
        raised = False
        try:
            repr(Experiment.objects.filter(end__lt=F('start') * self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to multiply datetime by timedelta.")

    def test_delta_invalid_op_div(self):
        raised = False
        try:
            repr(Experiment.objects.filter(end__lt=F('start') / self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to divide datetime by timedelta.")

    def test_delta_invalid_op_mod(self):
        raised = False
        try:
            repr(Experiment.objects.filter(end__lt=F('start') % self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to modulo divide datetime by timedelta.")

    def test_delta_invalid_op_and(self):
        raised = False
        try:
            repr(Experiment.objects.filter(end__lt=F('start').bitand(self.deltas[0])))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to binary and a datetime with a timedelta.")

    def test_delta_invalid_op_or(self):
        raised = False
        try:
            repr(Experiment.objects.filter(end__lt=F('start').bitor(self.deltas[0])))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to binary or a datetime with a timedelta.")
