from django.test import TestCase
from django.db import models
from django.db.models import Case, When, Q, Value, BooleanField

class Application(models.Model):
    pass

class Score(models.Model):
    application = models.ForeignKey(Application, on_delete=models.PROTECT, null=True, blank=True)
    reviewed = models.BooleanField(null=True)

class NegatedQWhenBugTest(TestCase):
    def setUp(self):
        a1 = Application.objects.create()
        Score.objects.create(application=a1, reviewed=False)
        Score.objects.create(application=a1, reviewed=True)
        Application.objects.create()  # a2, no Score

    def test_negated_q_in_when_vs_filter(self):
        qs1 = Application.objects.annotate(
            needs_review=Case(
                When(~Q(score__reviewed=True), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).filter(needs_review=True)

        qs2 = Application.objects.filter(~Q(score__reviewed=True))

        # This currently fails on buggy ORM behavior — outputs differ
        self.assertSetEqual(set(qs1), set(qs2))

    def test_negated_q_with_null_scores(self):
    # Add an Application with a Score that has reviewed=None
        a3 = Application.objects.create()
        Score.objects.create(application=a3, reviewed=None)

        qs1 = Application.objects.annotate(
            needs_review=Case(
                When(~Q(score__reviewed=True), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).filter(needs_review=True).order_by('id')

        qs2 = Application.objects.filter(~Q(score__reviewed=True)).order_by('id')

        print("qs1 SQL:", qs1.query)
        print("qs2 SQL:", qs2.query)
        print("qs1 results:", list(qs1.values_list('id', flat=True)))
        print("qs2 results:", list(qs2.values_list('id', flat=True)))

        self.assertSetEqual(set(qs1), set(qs2))
