"""
Spanning tests for all the operations that F() expressions can perform.
"""
from __future__ import absolute_import

import datetime

from django.db import connection
from django.db.models import F
from django.test import TestCase, Approximate, skipUnlessDBFeature

from .models import Number, Experiment


class ExpressionsRegressTests(TestCase):

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
                                .update(float=F('integer') + F('float') * 2),
                          1)

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
        end = stime+delta0
        e0 = Experiment.objects.create(name='e0', assigned=sday, start=stime,
            end=end, completed=end.date())
        self.deltas.append(delta0)
        self.delays.append(e0.start-
            datetime.datetime.combine(e0.assigned, midnight))
        self.days_long.append(e0.completed-e0.assigned)

        # e1: started one day after assigned, tiny duration, data
        # set so that end time has no fractional seconds, which
        # tests an edge case on sqlite. This Experiment is only
        # included in the test data when the DB supports microsecond
        # precision.
        if connection.features.supports_microsecond_precision:
            delay = datetime.timedelta(1)
            end = stime + delay + delta1
            e1 = Experiment.objects.create(name='e1', assigned=sday,
                start=stime+delay, end=end, completed=end.date())
            self.deltas.append(delta1)
            self.delays.append(e1.start-
                datetime.datetime.combine(e1.assigned, midnight))
            self.days_long.append(e1.completed-e1.assigned)

        # e2: started three days after assigned, small duration
        end = stime+delta2
        e2 = Experiment.objects.create(name='e2',
            assigned=sday-datetime.timedelta(3), start=stime, end=end,
            completed=end.date())
        self.deltas.append(delta2)
        self.delays.append(e2.start-
            datetime.datetime.combine(e2.assigned, midnight))
        self.days_long.append(e2.completed-e2.assigned)

        # e3: started four days after assigned, medium duration
        delay = datetime.timedelta(4)
        end = stime + delay + delta3
        e3 = Experiment.objects.create(name='e3',
            assigned=sday, start=stime+delay, end=end, completed=end.date())
        self.deltas.append(delta3)
        self.delays.append(e3.start-
            datetime.datetime.combine(e3.assigned, midnight))
        self.days_long.append(e3.completed-e3.assigned)

        # e4: started 10 days after assignment, long duration
        end = stime + delta4
        e4 = Experiment.objects.create(name='e4',
            assigned=sday-datetime.timedelta(10), start=stime, end=end,
            completed=end.date())
        self.deltas.append(delta4)
        self.delays.append(e4.start-
            datetime.datetime.combine(e4.assigned, midnight))
        self.days_long.append(e4.completed-e4.assigned)
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
                Experiment.objects.filter(end__lt=F('start')+delta)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(end__lte=F('start')+delta)]
            self.assertEqual(test_set, self.expnames[:i+1])

    def test_delta_subtract(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            test_set = [e.name for e in
                Experiment.objects.filter(start__gt=F('end')-delta)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(start__gte=F('end')-delta)]
            self.assertEqual(test_set, self.expnames[:i+1])

    def test_exclude(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            test_set = [e.name for e in
                Experiment.objects.exclude(end__lt=F('start')+delta)]
            self.assertEqual(test_set, self.expnames[i:])

            test_set = [e.name for e in
                Experiment.objects.exclude(end__lte=F('start')+delta)]
            self.assertEqual(test_set, self.expnames[i+1:])

    def test_date_comparison(self):
        for i in range(len(self.days_long)):
            days = self.days_long[i]
            test_set = [e.name for e in
                Experiment.objects.filter(completed__lt=F('assigned')+days)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(completed__lte=F('assigned')+days)]
            self.assertEqual(test_set, self.expnames[:i+1])

    @skipUnlessDBFeature("supports_mixed_date_datetime_comparisons")
    def test_mixed_comparisons1(self):
        for i in range(len(self.delays)):
            delay = self.delays[i]
            if not connection.features.supports_microsecond_precision:
                delay = datetime.timedelta(delay.days, delay.seconds)
            test_set = [e.name for e in
                Experiment.objects.filter(assigned__gt=F('start')-delay)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(assigned__gte=F('start')-delay)]
            self.assertEqual(test_set, self.expnames[:i+1])

    def test_mixed_comparisons2(self):
        delays = [datetime.timedelta(delay.days) for delay in self.delays]
        for i in range(len(delays)):
            delay = delays[i]
            test_set = [e.name for e in
                Experiment.objects.filter(start__lt=F('assigned')+delay)]
            self.assertEqual(test_set, self.expnames[:i])

            test_set = [e.name for e in
                Experiment.objects.filter(start__lte=F('assigned')+delay+
                    datetime.timedelta(1))]
            self.assertEqual(test_set, self.expnames[:i+1])

    def test_delta_update(self):
        for i in range(len(self.deltas)):
            delta = self.deltas[i]
            exps = Experiment.objects.all()
            expected_durations = [e.duration() for e in exps]
            expected_starts = [e.start+delta for e in exps]
            expected_ends = [e.end+delta for e in exps]

            Experiment.objects.update(start=F('start')+delta, end=F('end')+delta)
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
            r = repr(Experiment.objects.filter(end__lt=F('start')*self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to multiply datetime by timedelta.")

    def test_delta_invalid_op_div(self):
        raised = False
        try:
            r = repr(Experiment.objects.filter(end__lt=F('start')/self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to divide datetime by timedelta.")

    def test_delta_invalid_op_mod(self):
        raised = False
        try:
            r = repr(Experiment.objects.filter(end__lt=F('start')%self.deltas[0]))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to modulo divide datetime by timedelta.")

    def test_delta_invalid_op_and(self):
        raised = False
        try:
            r = repr(Experiment.objects.filter(end__lt=F('start').bitand(self.deltas[0])))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to binary and a datetime with a timedelta.")

    def test_delta_invalid_op_or(self):
        raised = False
        try:
            r = repr(Experiment.objects.filter(end__lt=F('start').bitor(self.deltas[0])))
        except TypeError:
            raised = True
        self.assertTrue(raised, "TypeError not raised on attempt to binary or a datetime with a timedelta.")
