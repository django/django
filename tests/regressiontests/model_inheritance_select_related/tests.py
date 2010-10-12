from operator import attrgetter

from django.test import TestCase

from models import Restaurant, Person


class ModelInheritanceSelectRelatedTests(TestCase):
    def test_inherited_select_related(self):
        # Regression test for #7246
        r1 = Restaurant.objects.create(
            name="Nobu", serves_sushi=True, serves_steak=False
        )
        r2 = Restaurant.objects.create(
            name="Craft", serves_sushi=False, serves_steak=True
        )
        p1 = Person.objects.create(name="John", favorite_restaurant=r1)
        p2 = Person.objects.create(name="Jane", favorite_restaurant=r2)

        self.assertQuerysetEqual(
            Person.objects.order_by("name").select_related(), [
                "Jane",
                "John",
            ],
            attrgetter("name")
        )

        jane = Person.objects.order_by("name").select_related("favorite_restaurant")[0]
        self.assertEqual(jane.favorite_restaurant.name, "Craft")
