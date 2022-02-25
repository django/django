"""
Regression tests for Model inheritance behavior.
"""
import datetime
from operator import attrgetter
from unittest import expectedFailure

from django import forms
from django.test import TestCase

from .models import (
    ArticleWithAuthor,
    BachelorParty,
    BirthdayParty,
    BusStation,
    Child,
    Congressman,
    DerivedM,
    InternalCertificationAudit,
    ItalianRestaurant,
    M2MChild,
    MessyBachelorParty,
    ParkingLot,
    ParkingLot3,
    ParkingLot4A,
    ParkingLot4B,
    Person,
    Place,
    Politician,
    Profile,
    QualityControl,
    Restaurant,
    SelfRefChild,
    SelfRefParent,
    Senator,
    Supplier,
    TrainStation,
    User,
    Wholesaler,
)


class ModelInheritanceTest(TestCase):
    def test_model_inheritance(self):
        # Regression for #7350, #7202
        # When you create a Parent object with a specific reference to an
        # existent child instance, saving the Parent doesn't duplicate the
        # child. This behavior is only activated during a raw save - it is
        # mostly relevant to deserialization, but any sort of CORBA style
        # 'narrow()' API would require a similar approach.

        # Create a child-parent-grandparent chain
        place1 = Place(name="Guido's House of Pasta", address="944 W. Fullerton")
        place1.save_base(raw=True)
        restaurant = Restaurant(
            place_ptr=place1,
            serves_hot_dogs=True,
            serves_pizza=False,
        )
        restaurant.save_base(raw=True)
        italian_restaurant = ItalianRestaurant(
            restaurant_ptr=restaurant, serves_gnocchi=True
        )
        italian_restaurant.save_base(raw=True)

        # Create a child-parent chain with an explicit parent link
        place2 = Place(name="Main St", address="111 Main St")
        place2.save_base(raw=True)
        park = ParkingLot(parent=place2, capacity=100)
        park.save_base(raw=True)

        # No extra parent objects have been created.
        places = list(Place.objects.all())
        self.assertEqual(places, [place1, place2])

        dicts = list(Restaurant.objects.values("name", "serves_hot_dogs"))
        self.assertEqual(
            dicts, [{"name": "Guido's House of Pasta", "serves_hot_dogs": True}]
        )

        dicts = list(
            ItalianRestaurant.objects.values(
                "name", "serves_hot_dogs", "serves_gnocchi"
            )
        )
        self.assertEqual(
            dicts,
            [
                {
                    "name": "Guido's House of Pasta",
                    "serves_gnocchi": True,
                    "serves_hot_dogs": True,
                }
            ],
        )

        dicts = list(ParkingLot.objects.values("name", "capacity"))
        self.assertEqual(
            dicts,
            [
                {
                    "capacity": 100,
                    "name": "Main St",
                }
            ],
        )

        # You can also update objects when using a raw save.
        place1.name = "Guido's All New House of Pasta"
        place1.save_base(raw=True)

        restaurant.serves_hot_dogs = False
        restaurant.save_base(raw=True)

        italian_restaurant.serves_gnocchi = False
        italian_restaurant.save_base(raw=True)

        place2.name = "Derelict lot"
        place2.save_base(raw=True)

        park.capacity = 50
        park.save_base(raw=True)

        # No extra parent objects after an update, either.
        places = list(Place.objects.all())
        self.assertEqual(places, [place2, place1])
        self.assertEqual(places[0].name, "Derelict lot")
        self.assertEqual(places[1].name, "Guido's All New House of Pasta")

        dicts = list(Restaurant.objects.values("name", "serves_hot_dogs"))
        self.assertEqual(
            dicts,
            [
                {
                    "name": "Guido's All New House of Pasta",
                    "serves_hot_dogs": False,
                }
            ],
        )

        dicts = list(
            ItalianRestaurant.objects.values(
                "name", "serves_hot_dogs", "serves_gnocchi"
            )
        )
        self.assertEqual(
            dicts,
            [
                {
                    "name": "Guido's All New House of Pasta",
                    "serves_gnocchi": False,
                    "serves_hot_dogs": False,
                }
            ],
        )

        dicts = list(ParkingLot.objects.values("name", "capacity"))
        self.assertEqual(
            dicts,
            [
                {
                    "capacity": 50,
                    "name": "Derelict lot",
                }
            ],
        )

        # If you try to raw_save a parent attribute onto a child object,
        # the attribute will be ignored.

        italian_restaurant.name = "Lorenzo's Pasta Hut"
        italian_restaurant.save_base(raw=True)

        # Note that the name has not changed
        # - name is an attribute of Place, not ItalianRestaurant
        dicts = list(
            ItalianRestaurant.objects.values(
                "name", "serves_hot_dogs", "serves_gnocchi"
            )
        )
        self.assertEqual(
            dicts,
            [
                {
                    "name": "Guido's All New House of Pasta",
                    "serves_gnocchi": False,
                    "serves_hot_dogs": False,
                }
            ],
        )

    def test_issue_7105(self):
        # Regressions tests for #7105: dates() queries should be able to use
        # fields from the parent model as easily as the child.
        Child.objects.create(
            name="child", created=datetime.datetime(2008, 6, 26, 17, 0, 0)
        )
        datetimes = list(Child.objects.datetimes("created", "month"))
        self.assertEqual(datetimes, [datetime.datetime(2008, 6, 1, 0, 0)])

    def test_issue_7276(self):
        # Regression test for #7276: calling delete() on a model with
        # multi-table inheritance should delete the associated rows from any
        # ancestor tables, as well as any descendent objects.
        place1 = Place(name="Guido's House of Pasta", address="944 W. Fullerton")
        place1.save_base(raw=True)
        restaurant = Restaurant(
            place_ptr=place1,
            serves_hot_dogs=True,
            serves_pizza=False,
        )
        restaurant.save_base(raw=True)
        italian_restaurant = ItalianRestaurant(
            restaurant_ptr=restaurant, serves_gnocchi=True
        )
        italian_restaurant.save_base(raw=True)

        ident = ItalianRestaurant.objects.all()[0].id
        self.assertEqual(Place.objects.get(pk=ident), place1)
        Restaurant.objects.create(
            name="a",
            address="xx",
            serves_hot_dogs=True,
            serves_pizza=False,
        )

        # This should delete both Restaurants, plus the related places, plus
        # the ItalianRestaurant.
        Restaurant.objects.all().delete()

        with self.assertRaises(Place.DoesNotExist):
            Place.objects.get(pk=ident)
        with self.assertRaises(ItalianRestaurant.DoesNotExist):
            ItalianRestaurant.objects.get(pk=ident)

    def test_issue_6755(self):
        """
        Regression test for #6755
        """
        r = Restaurant(serves_pizza=False, serves_hot_dogs=False)
        r.save()
        self.assertEqual(r.id, r.place_ptr_id)
        orig_id = r.id
        r = Restaurant(place_ptr_id=orig_id, serves_pizza=True, serves_hot_dogs=False)
        r.save()
        self.assertEqual(r.id, orig_id)
        self.assertEqual(r.id, r.place_ptr_id)

    def test_issue_11764(self):
        """
        Regression test for #11764
        """
        wholesalers = list(Wholesaler.objects.select_related())
        self.assertEqual(wholesalers, [])

    def test_issue_7853(self):
        """
        Regression test for #7853
        If the parent class has a self-referential link, make sure that any
        updates to that link via the child update the right table.
        """
        obj = SelfRefChild.objects.create(child_data=37, parent_data=42)
        obj.delete()

    def test_get_next_previous_by_date(self):
        """
        Regression tests for #8076
        get_(next/previous)_by_date should work
        """
        c1 = ArticleWithAuthor(
            headline="ArticleWithAuthor 1",
            author="Person 1",
            pub_date=datetime.datetime(2005, 8, 1, 3, 0),
        )
        c1.save()
        c2 = ArticleWithAuthor(
            headline="ArticleWithAuthor 2",
            author="Person 2",
            pub_date=datetime.datetime(2005, 8, 1, 10, 0),
        )
        c2.save()
        c3 = ArticleWithAuthor(
            headline="ArticleWithAuthor 3",
            author="Person 3",
            pub_date=datetime.datetime(2005, 8, 2),
        )
        c3.save()

        self.assertEqual(c1.get_next_by_pub_date(), c2)
        self.assertEqual(c2.get_next_by_pub_date(), c3)
        with self.assertRaises(ArticleWithAuthor.DoesNotExist):
            c3.get_next_by_pub_date()
        self.assertEqual(c3.get_previous_by_pub_date(), c2)
        self.assertEqual(c2.get_previous_by_pub_date(), c1)
        with self.assertRaises(ArticleWithAuthor.DoesNotExist):
            c1.get_previous_by_pub_date()

    def test_inherited_fields(self):
        """
        Regression test for #8825 and #9390
        Make sure all inherited fields (esp. m2m fields, in this case) appear
        on the child class.
        """
        m2mchildren = list(M2MChild.objects.filter(articles__isnull=False))
        self.assertEqual(m2mchildren, [])

        # Ordering should not include any database column more than once (this
        # is most likely to occur naturally with model inheritance, so we
        # check it here). Regression test for #9390. This necessarily pokes at
        # the SQL string for the query, since the duplicate problems are only
        # apparent at that late stage.
        qs = ArticleWithAuthor.objects.order_by("pub_date", "pk")
        sql = qs.query.get_compiler(qs.db).as_sql()[0]
        fragment = sql[sql.find("ORDER BY") :]
        pos = fragment.find("pub_date")
        self.assertEqual(fragment.find("pub_date", pos + 1), -1)

    def test_queryset_update_on_parent_model(self):
        """
        Regression test for #10362
        It is possible to call update() and only change a field in
        an ancestor model.
        """
        article = ArticleWithAuthor.objects.create(
            author="fred",
            headline="Hey there!",
            pub_date=datetime.datetime(2009, 3, 1, 8, 0, 0),
        )
        update = ArticleWithAuthor.objects.filter(author="fred").update(
            headline="Oh, no!"
        )
        self.assertEqual(update, 1)
        update = ArticleWithAuthor.objects.filter(pk=article.pk).update(
            headline="Oh, no!"
        )
        self.assertEqual(update, 1)

        derivedm1 = DerivedM.objects.create(
            customPK=44,
            base_name="b1",
            derived_name="d1",
        )
        self.assertEqual(derivedm1.customPK, 44)
        self.assertEqual(derivedm1.base_name, "b1")
        self.assertEqual(derivedm1.derived_name, "d1")
        derivedms = list(DerivedM.objects.all())
        self.assertEqual(derivedms, [derivedm1])

    def test_use_explicit_o2o_to_parent_as_pk(self):
        """
        The connector from child to parent need not be the pk on the child.
        """
        self.assertEqual(ParkingLot3._meta.pk.name, "primary_key")
        # the child->parent link
        self.assertEqual(ParkingLot3._meta.get_ancestor_link(Place).name, "parent")

    def test_use_explicit_o2o_to_parent_from_abstract_model(self):
        self.assertEqual(ParkingLot4A._meta.pk.name, "parent")
        ParkingLot4A.objects.create(
            name="Parking4A",
            address="21 Jump Street",
        )

        self.assertEqual(ParkingLot4B._meta.pk.name, "parent")
        ParkingLot4A.objects.create(
            name="Parking4B",
            address="21 Jump Street",
        )

    def test_all_fields_from_abstract_base_class(self):
        """
        Regression tests for #7588
        """
        # All fields from an ABC, including those inherited non-abstractly
        # should be available on child classes (#7588). Creating this instance
        # should work without error.
        QualityControl.objects.create(
            headline="Problems in Django",
            pub_date=datetime.datetime.now(),
            quality=10,
            assignee="adrian",
        )

    def test_abstract_base_class_m2m_relation_inheritance(self):
        # many-to-many relations defined on an abstract base class are
        # correctly inherited (and created) on the child class.
        p1 = Person.objects.create(name="Alice")
        p2 = Person.objects.create(name="Bob")
        p3 = Person.objects.create(name="Carol")
        p4 = Person.objects.create(name="Dave")

        birthday = BirthdayParty.objects.create(name="Birthday party for Alice")
        birthday.attendees.set([p1, p3])

        bachelor = BachelorParty.objects.create(name="Bachelor party for Bob")
        bachelor.attendees.set([p2, p4])

        parties = list(p1.birthdayparty_set.all())
        self.assertEqual(parties, [birthday])

        parties = list(p1.bachelorparty_set.all())
        self.assertEqual(parties, [])

        parties = list(p2.bachelorparty_set.all())
        self.assertEqual(parties, [bachelor])

        # A subclass of a subclass of an abstract model doesn't get its own
        # accessor.
        self.assertFalse(hasattr(p2, "messybachelorparty_set"))

        # ... but it does inherit the m2m from its parent
        messy = MessyBachelorParty.objects.create(name="Bachelor party for Dave")
        messy.attendees.set([p4])
        messy_parent = messy.bachelorparty_ptr

        parties = list(p4.bachelorparty_set.all())
        self.assertEqual(parties, [bachelor, messy_parent])

    def test_abstract_base_class_m2m_relation_inheritance_manager_reused(self):
        p1 = Person.objects.create(name="Alice")
        self.assertIs(p1.birthdayparty_set, p1.birthdayparty_set)
        self.assertIs(p1.bachelorparty_set, p1.bachelorparty_set)

    def test_abstract_verbose_name_plural_inheritance(self):
        """
        verbose_name_plural correctly inherited from ABC if inheritance chain
        includes an abstract model.
        """
        # Regression test for #11369: verbose_name_plural should be inherited
        # from an ABC even when there are one or more intermediate
        # abstract models in the inheritance chain, for consistency with
        # verbose_name.
        self.assertEqual(InternalCertificationAudit._meta.verbose_name_plural, "Audits")

    def test_inherited_nullable_exclude(self):
        obj = SelfRefChild.objects.create(child_data=37, parent_data=42)
        self.assertQuerysetEqual(
            SelfRefParent.objects.exclude(self_data=72), [obj.pk], attrgetter("pk")
        )
        self.assertQuerysetEqual(
            SelfRefChild.objects.exclude(self_data=72), [obj.pk], attrgetter("pk")
        )

    def test_concrete_abstract_concrete_pk(self):
        """
        Primary key set correctly with concrete->abstract->concrete inheritance.
        """
        # Regression test for #13987: Primary key is incorrectly determined
        # when more than one model has a concrete->abstract->concrete
        # inheritance hierarchy.
        self.assertEqual(
            len(
                [field for field in BusStation._meta.local_fields if field.primary_key]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    field
                    for field in TrainStation._meta.local_fields
                    if field.primary_key
                ]
            ),
            1,
        )
        self.assertIs(BusStation._meta.pk.model, BusStation)
        self.assertIs(TrainStation._meta.pk.model, TrainStation)

    def test_inherited_unique_field_with_form(self):
        """
        A model which has different primary key for the parent model passes
        unique field checking correctly (#17615).
        """

        class ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
                fields = "__all__"

        User.objects.create(username="user_only")
        p = Profile.objects.create(username="user_with_profile")
        form = ProfileForm(
            {"username": "user_with_profile", "extra": "hello"}, instance=p
        )
        self.assertTrue(form.is_valid())

    def test_inheritance_joins(self):
        # Test for #17502 - check that filtering through two levels of
        # inheritance chain doesn't generate extra joins.
        qs = ItalianRestaurant.objects.all()
        self.assertEqual(str(qs.query).count("JOIN"), 2)
        qs = ItalianRestaurant.objects.filter(name="foo")
        self.assertEqual(str(qs.query).count("JOIN"), 2)

    @expectedFailure
    def test_inheritance_values_joins(self):
        # It would be nice (but not too important) to skip the middle join in
        # this case. Skipping is possible as nothing from the middle model is
        # used in the qs and top contains direct pointer to the bottom model.
        qs = ItalianRestaurant.objects.values_list("serves_gnocchi").filter(name="foo")
        self.assertEqual(str(qs.query).count("JOIN"), 1)

    def test_issue_21554(self):
        senator = Senator.objects.create(name="John Doe", title="X", state="Y")
        senator = Senator.objects.get(pk=senator.pk)
        self.assertEqual(senator.name, "John Doe")
        self.assertEqual(senator.title, "X")
        self.assertEqual(senator.state, "Y")

    def test_inheritance_resolve_columns(self):
        Restaurant.objects.create(
            name="Bobs Cafe",
            address="Somewhere",
            serves_pizza=True,
            serves_hot_dogs=True,
        )
        p = Place.objects.select_related("restaurant")[0]
        self.assertIsInstance(p.restaurant.serves_pizza, bool)

    def test_inheritance_select_related(self):
        # Regression test for #7246
        r1 = Restaurant.objects.create(
            name="Nobu", serves_hot_dogs=True, serves_pizza=False
        )
        r2 = Restaurant.objects.create(
            name="Craft", serves_hot_dogs=False, serves_pizza=True
        )
        Supplier.objects.create(name="John", restaurant=r1)
        Supplier.objects.create(name="Jane", restaurant=r2)

        self.assertQuerysetEqual(
            Supplier.objects.order_by("name").select_related(),
            [
                "Jane",
                "John",
            ],
            attrgetter("name"),
        )

        jane = Supplier.objects.order_by("name").select_related("restaurant")[0]
        self.assertEqual(jane.restaurant.name, "Craft")

    def test_filter_with_parent_fk(self):
        r = Restaurant.objects.create()
        s = Supplier.objects.create(restaurant=r)
        # The mismatch between Restaurant and Place is intentional (#28175).
        self.assertSequenceEqual(
            Supplier.objects.filter(restaurant__in=Place.objects.all()), [s]
        )

    def test_ptr_accessor_assigns_state(self):
        r = Restaurant.objects.create()
        self.assertIs(r.place_ptr._state.adding, False)
        self.assertEqual(r.place_ptr._state.db, "default")

    def test_related_filtering_query_efficiency_ticket_15844(self):
        r = Restaurant.objects.create(
            name="Guido's House of Pasta",
            address="944 W. Fullerton",
            serves_hot_dogs=True,
            serves_pizza=False,
        )
        s = Supplier.objects.create(restaurant=r)
        with self.assertNumQueries(1):
            self.assertSequenceEqual(Supplier.objects.filter(restaurant=r), [s])
        with self.assertNumQueries(1):
            self.assertSequenceEqual(r.supplier_set.all(), [s])

    def test_queries_on_parent_access(self):
        italian_restaurant = ItalianRestaurant.objects.create(
            name="Guido's House of Pasta",
            address="944 W. Fullerton",
            serves_hot_dogs=True,
            serves_pizza=False,
            serves_gnocchi=True,
        )

        # No queries are made when accessing the parent objects.
        italian_restaurant = ItalianRestaurant.objects.get(pk=italian_restaurant.pk)
        with self.assertNumQueries(0):
            restaurant = italian_restaurant.restaurant_ptr
            self.assertEqual(restaurant.place_ptr.restaurant, restaurant)
            self.assertEqual(restaurant.italianrestaurant, italian_restaurant)

        # One query is made when accessing the parent objects when the instance
        # is deferred.
        italian_restaurant = ItalianRestaurant.objects.only("serves_gnocchi").get(
            pk=italian_restaurant.pk
        )
        with self.assertNumQueries(1):
            restaurant = italian_restaurant.restaurant_ptr
            self.assertEqual(restaurant.place_ptr.restaurant, restaurant)
            self.assertEqual(restaurant.italianrestaurant, italian_restaurant)

        # No queries are made when accessing the parent objects when the
        # instance has deferred a field not present in the parent table.
        italian_restaurant = ItalianRestaurant.objects.defer("serves_gnocchi").get(
            pk=italian_restaurant.pk
        )
        with self.assertNumQueries(0):
            restaurant = italian_restaurant.restaurant_ptr
            self.assertEqual(restaurant.place_ptr.restaurant, restaurant)
            self.assertEqual(restaurant.italianrestaurant, italian_restaurant)

    def test_id_field_update_on_ancestor_change(self):
        place1 = Place.objects.create(name="House of Pasta", address="944 Fullerton")
        place2 = Place.objects.create(name="House of Pizza", address="954 Fullerton")
        place3 = Place.objects.create(name="Burger house", address="964 Fullerton")
        restaurant1 = Restaurant.objects.create(
            place_ptr=place1,
            serves_hot_dogs=True,
            serves_pizza=False,
        )
        restaurant2 = Restaurant.objects.create(
            place_ptr=place2,
            serves_hot_dogs=True,
            serves_pizza=False,
        )

        italian_restaurant = ItalianRestaurant.objects.create(
            restaurant_ptr=restaurant1,
            serves_gnocchi=True,
        )
        # Changing the parent of a restaurant changes the restaurant's ID & PK.
        restaurant1.place_ptr = place3
        self.assertEqual(restaurant1.pk, place3.pk)
        self.assertEqual(restaurant1.id, place3.id)
        self.assertEqual(restaurant1.pk, restaurant1.id)
        restaurant1.place_ptr = None
        self.assertIsNone(restaurant1.pk)
        self.assertIsNone(restaurant1.id)
        # Changing the parent of an italian restaurant changes the restaurant's
        # ID & PK.
        italian_restaurant.restaurant_ptr = restaurant2
        self.assertEqual(italian_restaurant.pk, restaurant2.pk)
        self.assertEqual(italian_restaurant.id, restaurant2.id)
        self.assertEqual(italian_restaurant.pk, italian_restaurant.id)
        italian_restaurant.restaurant_ptr = None
        self.assertIsNone(italian_restaurant.pk)
        self.assertIsNone(italian_restaurant.id)

    def test_create_new_instance_with_pk_equals_none(self):
        p1 = Profile.objects.create(username="john")
        p2 = User.objects.get(pk=p1.user_ptr_id).profile
        # Create a new profile by setting pk = None.
        p2.pk = None
        p2.user_ptr_id = None
        p2.username = "bill"
        p2.save()
        self.assertEqual(Profile.objects.count(), 2)
        self.assertEqual(User.objects.get(pk=p1.user_ptr_id).username, "john")

    def test_create_new_instance_with_pk_equals_none_multi_inheritance(self):
        c1 = Congressman.objects.create(state="PA", name="John", title="senator 1")
        c2 = Person.objects.get(pk=c1.pk).congressman
        # Create a new congressman by setting pk = None.
        c2.pk = None
        c2.id = None
        c2.politician_ptr_id = None
        c2.name = "Bill"
        c2.title = "senator 2"
        c2.save()
        self.assertEqual(Congressman.objects.count(), 2)
        self.assertEqual(Person.objects.get(pk=c1.pk).name, "John")
        self.assertEqual(
            Politician.objects.get(pk=c1.politician_ptr_id).title,
            "senator 1",
        )
