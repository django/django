from __future__ import absolute_import

from django.test import TestCase

from .models import (
    BathRoom,
    Building,
    Cafeteria,
    ClassRoom,
    Office,
)


class RelatedNameTests(TestCase):

    def setUp(self):
        building = Building.objects.create(name="Django HQ")
        BathRoom.objects.create(building=building, room_number=1)
        Cafeteria.objects.create(building=building, room_number=2)
        ClassRoom.objects.create(building=building, room_number=3)
        Office.objects.create(building=building, room_number=4)

    # Abbreviations in function names to keep them from getting too long
    # rn - related_name
    # rqn - related_query_name

    def test_rn_with_no_rn_and_no_rqn(self):
        building = Building.objects.get(name="Django HQ")
        self.assertEquals(building.classroom_set.get().room_number, 3)

    def test_rqn_with_no_rn_and_no_rqn(self):
        building = Building.objects.get(classroom__room_number=3)
        self.assertEquals(building.name, "Django HQ")

    def test_rn_with_rn_and_no_rqn(self):
        building = Building.objects.get(name="Django HQ")
        self.assertEquals(building.offices.get().room_number, 4)

    def test_rqn_with_rn_and_no_rqn(self):
        building = Building.objects.get(offices__room_number=4)
        self.assertEquals(building.name, "Django HQ")

    def test_rn_with_no_rn_and_rqn(self):
        building = Building.objects.get(name="Django HQ")
        self.assertEquals(building.cafeteria_set.get().room_number, 2)

    def test_rqn_with_no_rn_and_rqn(self):
        building = Building.objects.get(cafe__room_number=2)
        self.assertEquals(building.name, "Django HQ")

    def test_rn_with_rn_and_rqn(self):
        building = Building.objects.get(name="Django HQ")
        self.assertEquals(building.loo_set.get().room_number, 1)

    def test_rqn_with_rn_and_rqn(self):
        building = Building.objects.get(wc__room_number=1)
        self.assertEquals(building.name, "Django HQ")
