from __future__ import unicode_literals

from django.test import TestCase

from .models import Flea, House, Person, Pet, Room


class UUIDPrefetchRelated(TestCase):

    def test_prefetch_related_from_uuid_model(self):
        Pet.objects.create(name='Fifi').people.add(
            Person.objects.create(name='Ellen'),
            Person.objects.create(name='George'),
        )

        with self.assertNumQueries(2):
            pet = Pet.objects.prefetch_related('people').get(name='Fifi')
        with self.assertNumQueries(0):
            self.assertEqual(2, len(pet.people.all()))

    def test_prefetch_related_to_uuid_model(self):
        Person.objects.create(name='Bella').pets.add(
            Pet.objects.create(name='Socks'),
            Pet.objects.create(name='Coffee'),
        )

        with self.assertNumQueries(2):
            person = Person.objects.prefetch_related('pets').get(name='Bella')
        with self.assertNumQueries(0):
            self.assertEqual(2, len(person.pets.all()))

    def test_prefetch_related_from_uuid_model_to_uuid_model(self):
        fleas = [Flea.objects.create() for i in range(3)]
        Pet.objects.create(name='Fifi').fleas_hosted.add(*fleas)
        Pet.objects.create(name='Bobo').fleas_hosted.add(*fleas)

        with self.assertNumQueries(2):
            pet = Pet.objects.prefetch_related('fleas_hosted').get(name='Fifi')
        with self.assertNumQueries(0):
            self.assertEqual(3, len(pet.fleas_hosted.all()))

        with self.assertNumQueries(2):
            flea = Flea.objects.prefetch_related('pets_visited').get(pk=fleas[0].pk)
        with self.assertNumQueries(0):
            self.assertEqual(2, len(flea.pets_visited.all()))

    def test_prefetch_related_from_uuid_model_to_uuid_model_with_values_flat(self):
        pet = Pet.objects.create(name='Fifi')
        pet.people.add(
            Person.objects.create(name='Ellen'),
            Person.objects.create(name='George'),
        )
        self.assertSequenceEqual(
            Pet.objects.prefetch_related('fleas_hosted').values_list('id', flat=True),
            [pet.id]
        )


class UUIDPrefetchRelatedLookups(TestCase):

    @classmethod
    def setUpTestData(cls):
        house = House.objects.create(name='Redwood', address='Arcata')
        room = Room.objects.create(name='Racoon', house=house)
        fleas = [Flea.objects.create(current_room=room) for i in range(3)]
        pet = Pet.objects.create(name='Spooky')
        pet.fleas_hosted.add(*fleas)
        person = Person.objects.create(name='Bob')
        person.houses.add(house)
        person.pets.add(pet)
        person.fleas_hosted.add(*fleas)

    def test_from_uuid_pk_lookup_uuid_pk_integer_pk(self):
        # From uuid-pk model, prefetch <uuid-pk model>.<integer-pk model>:
        with self.assertNumQueries(4):
            spooky = Pet.objects.prefetch_related('fleas_hosted__current_room__house').get(name='Spooky')
        with self.assertNumQueries(0):
            self.assertEqual('Racoon', spooky.fleas_hosted.all()[0].current_room.name)

    def test_from_uuid_pk_lookup_integer_pk2_uuid_pk2(self):
        # From uuid-pk model, prefetch <integer-pk model>.<integer-pk model>.<uuid-pk model>.<uuid-pk model>:
        with self.assertNumQueries(5):
            spooky = Pet.objects.prefetch_related('people__houses__rooms__fleas').get(name='Spooky')
        with self.assertNumQueries(0):
            self.assertEqual(3, len(spooky.people.all()[0].houses.all()[0].rooms.all()[0].fleas.all()))

    def test_from_integer_pk_lookup_uuid_pk_integer_pk(self):
        # From integer-pk model, prefetch <uuid-pk model>.<integer-pk model>:
        with self.assertNumQueries(3):
            racoon = Room.objects.prefetch_related('fleas__people_visited').get(name='Racoon')
        with self.assertNumQueries(0):
            self.assertEqual('Bob', racoon.fleas.all()[0].people_visited.all()[0].name)

    def test_from_integer_pk_lookup_integer_pk_uuid_pk(self):
        # From integer-pk model, prefetch <integer-pk model>.<uuid-pk model>:
        with self.assertNumQueries(3):
            redwood = House.objects.prefetch_related('rooms__fleas').get(name='Redwood')
        with self.assertNumQueries(0):
            self.assertEqual(3, len(redwood.rooms.all()[0].fleas.all()))

    def test_from_integer_pk_lookup_integer_pk_uuid_pk_uuid_pk(self):
        # From integer-pk model, prefetch <integer-pk model>.<uuid-pk model>.<uuid-pk model>:
        with self.assertNumQueries(4):
            redwood = House.objects.prefetch_related('rooms__fleas__pets_visited').get(name='Redwood')
        with self.assertNumQueries(0):
            self.assertEqual('Spooky', redwood.rooms.all()[0].fleas.all()[0].pets_visited.all()[0].name)
