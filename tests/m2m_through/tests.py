from datetime import datetime
from operator import attrgetter

from django.test import TestCase

from .models import (
    CustomMembership, Employee, Event, Friendship, Group, Ingredient,
    Invitation, Membership, Person, PersonSelfRefM2M, Recipe, RecipeIngredient,
    Relationship,
)


class M2mThroughTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = Person.objects.create(name='Bob')
        cls.jim = Person.objects.create(name='Jim')
        cls.jane = Person.objects.create(name='Jane')
        cls.rock = Group.objects.create(name='Rock')
        cls.roll = Group.objects.create(name='Roll')

    def test_retrieve_intermediate_items(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jane, group=self.rock)

        expected = ['Jane', 'Jim']
        self.assertQuerysetEqual(
            self.rock.members.all(),
            expected,
            attrgetter("name")
        )

    def test_get_on_intermediate_model(self):
        Membership.objects.create(person=self.jane, group=self.rock)

        queryset = Membership.objects.get(person=self.jane, group=self.rock)

        self.assertEqual(
            repr(queryset),
            '<Membership: Jane is a member of Rock>'
        )

    def test_filter_on_intermediate_model(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jane, group=self.rock)

        queryset = Membership.objects.filter(group=self.rock)

        expected = [
            '<Membership: Jim is a member of Rock>',
            '<Membership: Jane is a member of Rock>',
        ]

        self.assertQuerysetEqual(
            queryset,
            expected
        )

    def test_cannot_use_add_on_m2m_with_intermediary_model(self):
        msg = 'Cannot use add() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.rock.members.add(self.bob)

        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )

    def test_cannot_use_create_on_m2m_with_intermediary_model(self):
        msg = 'Cannot use create() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.rock.members.create(name='Annie')

        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )

    def test_cannot_use_remove_on_m2m_with_intermediary_model(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        msg = 'Cannot use remove() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.rock.members.remove(self.jim)

        self.assertQuerysetEqual(
            self.rock.members.all(),
            ['Jim'],
            attrgetter("name")
        )

    def test_cannot_use_setattr_on_m2m_with_intermediary_model(self):
        msg = 'Cannot set values on a ManyToManyField which specifies an intermediary model'
        members = list(Person.objects.filter(name__in=['Bob', 'Jim']))

        with self.assertRaisesMessage(AttributeError, msg):
            self.rock.members.set(members)

        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )

    def test_clear_removes_all_the_m2m_relationships(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jane, group=self.rock)

        self.rock.members.clear()

        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )

    def test_retrieve_reverse_intermediate_items(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jim, group=self.roll)

        expected = ['Rock', 'Roll']
        self.assertQuerysetEqual(
            self.jim.group_set.all(),
            expected,
            attrgetter("name")
        )

    def test_cannot_use_add_on_reverse_m2m_with_intermediary_model(self):
        msg = 'Cannot use add() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.bob.group_set.add(self.bob)

        self.assertQuerysetEqual(
            self.bob.group_set.all(),
            []
        )

    def test_cannot_use_create_on_reverse_m2m_with_intermediary_model(self):
        msg = 'Cannot use create() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.bob.group_set.create(name='Funk')

        self.assertQuerysetEqual(
            self.bob.group_set.all(),
            []
        )

    def test_cannot_use_remove_on_reverse_m2m_with_intermediary_model(self):
        Membership.objects.create(person=self.bob, group=self.rock)
        msg = 'Cannot use remove() on a ManyToManyField which specifies an intermediary model'

        with self.assertRaisesMessage(AttributeError, msg):
            self.bob.group_set.remove(self.rock)

        self.assertQuerysetEqual(
            self.bob.group_set.all(),
            ['Rock'],
            attrgetter('name')
        )

    def test_cannot_use_setattr_on_reverse_m2m_with_intermediary_model(self):
        msg = 'Cannot set values on a ManyToManyField which specifies an intermediary model'
        members = list(Group.objects.filter(name__in=['Rock', 'Roll']))

        with self.assertRaisesMessage(AttributeError, msg):
            self.bob.group_set.set(members)

        self.assertQuerysetEqual(
            self.bob.group_set.all(),
            []
        )

    def test_clear_on_reverse_removes_all_the_m2m_relationships(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jim, group=self.roll)

        self.jim.group_set.clear()

        self.assertQuerysetEqual(
            self.jim.group_set.all(),
            []
        )

    def test_query_model_by_attribute_name_of_related_model(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jane, group=self.rock)
        Membership.objects.create(person=self.bob, group=self.roll)
        Membership.objects.create(person=self.jim, group=self.roll)
        Membership.objects.create(person=self.jane, group=self.roll)

        self.assertQuerysetEqual(
            Group.objects.filter(members__name='Bob'),
            ['Roll'],
            attrgetter("name")
        )

    def test_order_by_relational_field_through_model(self):
        CustomMembership.objects.create(person=self.jim, group=self.rock)
        CustomMembership.objects.create(person=self.bob, group=self.rock)
        CustomMembership.objects.create(person=self.jane, group=self.roll)
        CustomMembership.objects.create(person=self.jim, group=self.roll)
        self.assertSequenceEqual(
            self.rock.custom_members.order_by('custom_person_related_name'),
            [self.jim, self.bob]
        )
        self.assertSequenceEqual(
            self.roll.custom_members.order_by('custom_person_related_name'),
            [self.jane, self.jim]
        )

    def test_query_first_model_by_intermediate_model_attribute(self):
        Membership.objects.create(
            person=self.jane, group=self.roll,
            invite_reason="She was just awesome."
        )
        Membership.objects.create(
            person=self.jim, group=self.roll,
            invite_reason="He is good."
        )
        Membership.objects.create(person=self.bob, group=self.roll)

        qs = Group.objects.filter(
            membership__invite_reason="She was just awesome."
        )
        self.assertQuerysetEqual(
            qs,
            ['Roll'],
            attrgetter("name")
        )

    def test_query_second_model_by_intermediate_model_attribute(self):
        Membership.objects.create(
            person=self.jane, group=self.roll,
            invite_reason="She was just awesome."
        )
        Membership.objects.create(
            person=self.jim, group=self.roll,
            invite_reason="He is good."
        )
        Membership.objects.create(person=self.bob, group=self.roll)

        qs = Person.objects.filter(
            membership__invite_reason="She was just awesome."
        )
        self.assertQuerysetEqual(
            qs,
            ['Jane'],
            attrgetter("name")
        )

    def test_query_model_by_related_model_name(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(person=self.jane, group=self.rock)
        Membership.objects.create(person=self.bob, group=self.roll)
        Membership.objects.create(person=self.jim, group=self.roll)
        Membership.objects.create(person=self.jane, group=self.roll)

        self.assertQuerysetEqual(
            Person.objects.filter(group__name="Rock"),
            ['Jane', 'Jim'],
            attrgetter("name")
        )

    def test_query_model_by_custom_related_name(self):
        CustomMembership.objects.create(person=self.bob, group=self.rock)
        CustomMembership.objects.create(person=self.jim, group=self.rock)

        self.assertQuerysetEqual(
            Person.objects.filter(custom__name="Rock"),
            ['Bob', 'Jim'],
            attrgetter("name")
        )

    def test_query_model_by_intermediate_can_return_non_unique_queryset(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        Membership.objects.create(
            person=self.jane, group=self.rock,
            date_joined=datetime(2006, 1, 1)
        )
        Membership.objects.create(
            person=self.bob, group=self.roll,
            date_joined=datetime(2004, 1, 1))
        Membership.objects.create(person=self.jim, group=self.roll)
        Membership.objects.create(
            person=self.jane, group=self.roll,
            date_joined=datetime(2004, 1, 1))

        qs = Person.objects.filter(
            membership__date_joined__gt=datetime(2004, 1, 1)
        )
        self.assertQuerysetEqual(
            qs,
            ['Jane', 'Jim', 'Jim'],
            attrgetter("name")
        )

    def test_custom_related_name_forward_empty_qs(self):
        self.assertQuerysetEqual(
            self.rock.custom_members.all(),
            []
        )

    def test_custom_related_name_reverse_empty_qs(self):
        self.assertQuerysetEqual(
            self.bob.custom.all(),
            []
        )

    def test_custom_related_name_forward_non_empty_qs(self):
        CustomMembership.objects.create(person=self.bob, group=self.rock)
        CustomMembership.objects.create(person=self.jim, group=self.rock)

        self.assertQuerysetEqual(
            self.rock.custom_members.all(),
            ['Bob', 'Jim'],
            attrgetter("name")
        )

    def test_custom_related_name_reverse_non_empty_qs(self):
        CustomMembership.objects.create(person=self.bob, group=self.rock)
        CustomMembership.objects.create(person=self.jim, group=self.rock)

        self.assertQuerysetEqual(
            self.bob.custom.all(),
            ['Rock'],
            attrgetter("name")
        )

    def test_custom_related_name_doesnt_conflict_with_fky_related_name(self):
        CustomMembership.objects.create(person=self.bob, group=self.rock)

        self.assertQuerysetEqual(
            self.bob.custom_person_related_name.all(),
            ['<CustomMembership: Bob is a member of Rock>']
        )

    def test_through_fields(self):
        """
        Relations with intermediary tables with multiple FKs
        to the M2M's ``to`` model are possible.
        """
        event = Event.objects.create(title='Rockwhale 2014')
        Invitation.objects.create(event=event, inviter=self.bob, invitee=self.jim)
        Invitation.objects.create(event=event, inviter=self.bob, invitee=self.jane)
        self.assertQuerysetEqual(
            event.invitees.all(),
            ['Jane', 'Jim'],
            attrgetter('name')
        )


class M2mThroughReferentialTests(TestCase):
    def test_self_referential_empty_qs(self):
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        self.assertQuerysetEqual(
            tony.friends.all(),
            []
        )

    def test_self_referential_non_symmetrical_first_side(self):
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        chris = PersonSelfRefM2M.objects.create(name="Chris")
        Friendship.objects.create(
            first=tony, second=chris, date_friended=datetime.now()
        )

        self.assertQuerysetEqual(
            tony.friends.all(),
            ['Chris'],
            attrgetter("name")
        )

    def test_self_referential_non_symmetrical_second_side(self):
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        chris = PersonSelfRefM2M.objects.create(name="Chris")
        Friendship.objects.create(
            first=tony, second=chris, date_friended=datetime.now()
        )

        self.assertQuerysetEqual(
            chris.friends.all(),
            []
        )

    def test_self_referential_non_symmetrical_clear_first_side(self):
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        chris = PersonSelfRefM2M.objects.create(name="Chris")
        Friendship.objects.create(
            first=tony, second=chris, date_friended=datetime.now()
        )

        chris.friends.clear()

        self.assertQuerysetEqual(
            chris.friends.all(),
            []
        )

        # Since this isn't a symmetrical relation, Tony's friend link still exists.
        self.assertQuerysetEqual(
            tony.friends.all(),
            ['Chris'],
            attrgetter("name")
        )

    def test_self_referential_symmetrical(self):
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        chris = PersonSelfRefM2M.objects.create(name="Chris")
        Friendship.objects.create(
            first=tony, second=chris, date_friended=datetime.now()
        )
        Friendship.objects.create(
            first=chris, second=tony, date_friended=datetime.now()
        )

        self.assertQuerysetEqual(
            tony.friends.all(),
            ['Chris'],
            attrgetter("name")
        )

        self.assertQuerysetEqual(
            chris.friends.all(),
            ['Tony'],
            attrgetter("name")
        )

    def test_through_fields_self_referential(self):
        john = Employee.objects.create(name='john')
        peter = Employee.objects.create(name='peter')
        mary = Employee.objects.create(name='mary')
        harry = Employee.objects.create(name='harry')

        Relationship.objects.create(source=john, target=peter, another=None)
        Relationship.objects.create(source=john, target=mary, another=None)
        Relationship.objects.create(source=john, target=harry, another=peter)

        self.assertQuerysetEqual(
            john.subordinates.all(),
            ['peter', 'mary', 'harry'],
            attrgetter('name')
        )


class M2mThroughToFieldsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pea = Ingredient.objects.create(iname='pea')
        cls.potato = Ingredient.objects.create(iname='potato')
        cls.tomato = Ingredient.objects.create(iname='tomato')
        cls.curry = Recipe.objects.create(rname='curry')
        RecipeIngredient.objects.create(recipe=cls.curry, ingredient=cls.potato)
        RecipeIngredient.objects.create(recipe=cls.curry, ingredient=cls.pea)
        RecipeIngredient.objects.create(recipe=cls.curry, ingredient=cls.tomato)

    def test_retrieval(self):
        # Forward retrieval
        self.assertSequenceEqual(self.curry.ingredients.all(), [self.pea, self.potato, self.tomato])
        # Backward retrieval
        self.assertEqual(self.tomato.recipes.get(), self.curry)

    def test_choices(self):
        field = Recipe._meta.get_field('ingredients')
        self.assertEqual(
            [choice[0] for choice in field.get_choices(include_blank=False)],
            ['pea', 'potato', 'tomato']
        )
