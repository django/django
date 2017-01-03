from __future__ import unicode_literals

from django.test import TestCase

from .models import (
    CompetingTeam, Event, Group, IndividualCompetitor, Membership, Person,
)


class MultiTableTests(TestCase):
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
        self.assertCountEqual(result, [self.team_alpha])

    def test_m2m_reverse_query(self):
        result = self.chris.event_set.all()
        self.assertCountEqual(result, [self.event])

    def test_m2m_query_proxied(self):
        result = self.event.special_people.all()
        self.assertCountEqual(result, [self.chris, self.dan])

    def test_m2m_reverse_query_proxied(self):
        result = self.chris.special_event_set.all()
        self.assertCountEqual(result, [self.event])

    def test_m2m_prefetch_proxied(self):
        result = Event.objects.filter(name='Exposition Match').prefetch_related('special_people')
        with self.assertNumQueries(2):
            self.assertCountEqual(result, [self.event])
            self.assertEqual(sorted([p.name for p in result[0].special_people.all()]), ['Chris', 'Dan'])

    def test_m2m_prefetch_reverse_proxied(self):
        result = Person.objects.filter(name='Dan').prefetch_related('special_event_set')
        with self.assertNumQueries(2):
            self.assertCountEqual(result, [self.dan])
            self.assertEqual([event.name for event in result[0].special_event_set.all()], ['Exposition Match'])
