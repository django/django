from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import Flea, House, Person, Pet, Room, TaggedUUIDItem, UUIDItem


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


class UUIDGenericForeignKeyTests(TestCase):
    """
    Tests for prefetch_related with GenericForeignKey pointing to models
    with UUID primary keys.
    """

    def test_prefetch_generic_foreign_key_with_uuid(self):
        """
        Test that prefetch_related works correctly when a GenericForeignKey
        points to a model with a UUID primary key.
        """
        # Create UUIDItem instances
        item1 = UUIDItem.objects.create(name='Item 1')
        item2 = UUIDItem.objects.create(name='Item 2')
        item3 = UUIDItem.objects.create(name='Item 3')

        # Get ContentType for UUIDItem
        ct = ContentType.objects.get_for_model(UUIDItem)

        # Create TaggedUUIDItem instances pointing to UUIDItem instances
        tag1 = TaggedUUIDItem.objects.create(
            tag='tag1',
            content_type=ct,
            object_id=str(item1.id)
        )
        tag2 = TaggedUUIDItem.objects.create(
            tag='tag2',
            content_type=ct,
            object_id=str(item2.id)
        )
        tag3 = TaggedUUIDItem.objects.create(
            tag='tag3',
            content_type=ct,
            object_id=str(item3.id)
        )

        # Test prefetch_related
        # Should do 2 queries: one for TaggedUUIDItem and one for UUIDItem
        with self.assertNumQueries(2):
            tags = list(TaggedUUIDItem.objects.prefetch_related('content_object'))

        # Now accessing content_object should not hit the database
        with self.assertNumQueries(0):
            self.assertEqual(tags[0].content_object.name, 'Item 1')
            self.assertEqual(tags[1].content_object.name, 'Item 2')
            self.assertEqual(tags[2].content_object.name, 'Item 3')

        # Verify the objects are properly linked
        self.assertEqual(tags[0].content_object.id, item1.id)
        self.assertEqual(tags[1].content_object.id, item2.id)
        self.assertEqual(tags[2].content_object.id, item3.id)

    def test_prefetch_generic_foreign_key_uuid_multiple_content_types(self):
        """
        Test that prefetch_related works correctly when GenericForeignKey
        points to multiple models, some with UUID primary keys.
        """
        # Create UUIDItem instances
        uuid_item = UUIDItem.objects.create(name='UUID Item')

        # Create a Bookmark instance (has integer pk)
        from .models import Bookmark
        bookmark = Bookmark.objects.create(url='http://example.com')

        # Get ContentTypes
        uuid_ct = ContentType.objects.get_for_model(UUIDItem)
        bookmark_ct = ContentType.objects.get_for_model(Bookmark)

        # Create TaggedUUIDItem instances pointing to different models
        tag1 = TaggedUUIDItem.objects.create(
            tag='uuid_tag',
            content_type=uuid_ct,
            object_id=str(uuid_item.id)
        )
        tag2 = TaggedUUIDItem.objects.create(
            tag='bookmark_tag',
            content_type=bookmark_ct,
            object_id=str(bookmark.id)
        )

        # Test prefetch_related with multiple content types
        with self.assertNumQueries(3):  # TaggedUUIDItem, UUIDItem, Bookmark
            tags = list(TaggedUUIDItem.objects.prefetch_related('content_object'))

        with self.assertNumQueries(0):
            self.assertEqual(tags[0].content_object.name, 'UUID Item')
            self.assertEqual(tags[1].content_object.url, 'http://example.com')
