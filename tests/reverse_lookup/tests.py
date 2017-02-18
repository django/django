from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.test import TestCase

from .models import Choice, Poll, User


class ReverseLookupTests(TestCase):

    def setUp(self):
        john = User.objects.create(name="John Doe")
        jim = User.objects.create(name="Jim Bo")
        first_poll = Poll.objects.create(
            question="What's the first question?",
            creator=john
        )
        second_poll = Poll.objects.create(
            question="What's the second question?",
            creator=jim
        )
        Choice.objects.create(
            poll=first_poll,
            related_poll=second_poll,
            name="This is the answer."
        )

    def test_reverse_by_field(self):
        u1 = User.objects.get(
            poll__question__exact="What's the first question?"
        )
        self.assertEqual(u1.name, "John Doe")

        u2 = User.objects.get(
            poll__question__exact="What's the second question?"
        )
        self.assertEqual(u2.name, "Jim Bo")

    def test_reverse_by_related_name(self):
        p1 = Poll.objects.get(poll_choice__name__exact="This is the answer.")
        self.assertEqual(p1.question, "What's the first question?")

        p2 = Poll.objects.get(
            related_choice__name__exact="This is the answer.")
        self.assertEqual(p2.question, "What's the second question?")

    def test_reverse_field_name_disallowed(self):
        """
        If a related_name is given you can't use the field name instead
        """
        self.assertRaises(FieldError, Poll.objects.get,
            choice__name__exact="This is the answer")
