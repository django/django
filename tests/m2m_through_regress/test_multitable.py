from __future__ import unicode_literals

from django.test import TestCase
from django.utils.six import assertCountEqual

from .models import (
    CompetingTeam, Event, Group, IndividualCompetitor, Membership, Person,
)


class M2MThroughMultiTableTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = Person.objects.create(name='Alice')
        cls.bob = Person.objects.create(name='Bob')
        cls.chris = Person.objects.create(name='Chris')
        cls.dan = Person.objects.create(name='Dan')
        cls.team_alpha = Group.objects.create(name='Alpha')
        Membership.objects.create(person=cls.alice, group=cls.team_alpha)
        Membership.objects.create(person=cls.bob, group=cls.team_alpha)
        cls.event = Event.objects.create(name='Exposition Match')
        IndividualCompetitor.objects.create(event=cls.event, person=cls.chris)
        IndividualCompetitor.objects.create(event=cls.event, person=cls.dan)
        CompetingTeam.objects.create(event=cls.event, team=cls.team_alpha)

    def test_m2m_query(self):
        result = self.event.teams.all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.team_alpha)

    def test_m2m_reverse_query(self):
        result = self.chris.event_set.all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.event)

    def test_m2m_query_proxied(self):
        result = self.event.special_people.all()
        self.assertQuerysetEqual(result, [repr(self.chris), repr(self.dan)], ordered=False)

    def test_m2m_reverse_query_proxied(self):
        result = self.chris.special_event_set.all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.event)

    def test_m2m_prefetch_proxied(self):
        result = Event.objects.filter(name='Exposition Match').prefetch_related('special_people')
        with self.assertNumQueries(2):
            self.assertEqual(len(result), 1)
            str(result[0].special_people.all())  # Access prefetched objects' attributes
            assertCountEqual(self, result[0].special_people.all(), (self.chris, self.dan))

    def test_m2m_prefetch_reverse_proxied(self):
        result = Person.objects.filter(name='Dan').prefetch_related('special_event_set')
        with self.assertNumQueries(2):
            self.assertEqual(len(result), 1)
            # Access prefetched objects' attributes
            str([event.name for event in result[0].special_event_set.all()])
            assertCountEqual(self, result[0].special_event_set.all(), [self.event])
