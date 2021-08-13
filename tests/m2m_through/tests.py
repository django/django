from datetime import date, datetime, timedelta
from operator import attrgetter

from django.db import IntegrityError
from django.test import TestCase

from .models import (
    CustomMembership, Employee, Event, Friendship, Group, Ingredient,
    Invitation, Membership, Person, PersonChild, PersonSelfRefM2M, Recipe,
    RecipeIngredient, Relationship, SymmetricalFriendship,
)


class M2mThroughTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = Person.objects.create(name='Bob')
        cls.jim = Person.objects.create(name='Jim')
        cls.jane = Person.objects.create(name='Jane')
        cls.rock = Group.objects.create(name='Rock')
        cls.roll = Group.objects.create(name='Roll')

    def test_reverse_inherited_m2m_with_through_fields_list_hashable(self):
        reverse_m2m = Person._meta.get_field('events_invited')
        self.assertEqual(reverse_m2m.through_fields, ['event', 'invitee'])
        inherited_reverse_m2m = PersonChild._meta.get_field('events_invited')
        self.assertEqual(inherited_reverse_m2m.through_fields, ['event', 'invitee'])
        self.assertEqual(hash(reverse_m2m), hash(inherited_reverse_m2m))

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
        m1 = Membership.objects.create(person=self.jim, group=self.rock)
        m2 = Membership.objects.create(person=self.jane, group=self.rock)

        queryset = Membership.objects.filter(group=self.rock)

        self.assertSequenceEqual(queryset, [m1, m2])

    def test_add_on_m2m_with_intermediate_model(self):
        self.rock.members.add(self.bob, through_defaults={'invite_reason': 'He is good.'})
        self.assertSequenceEqual(self.rock.members.all(), [self.bob])
        self.assertEqual(self.rock.membership_set.get().invite_reason, 'He is good.')

    def test_add_on_m2m_with_intermediate_model_callable_through_default(self):
        def invite_reason_callable():
            return 'They were good at %s' % datetime.now()

        self.rock.members.add(
            self.bob, self.jane,
            through_defaults={'invite_reason': invite_reason_callable},
        )
        self.assertSequenceEqual(self.rock.members.all(), [self.bob, self.jane])
        self.assertEqual(
            self.rock.membership_set.filter(
                invite_reason__startswith='They were good at ',
            ).count(),
            2,
        )
        # invite_reason_callable() is called once.
        self.assertEqual(
            self.bob.membership_set.get().invite_reason,
            self.jane.membership_set.get().invite_reason,
        )

    def test_set_on_m2m_with_intermediate_model_callable_through_default(self):
        self.rock.members.set(
            [self.bob, self.jane],
            through_defaults={'invite_reason': lambda: 'Why not?'},
        )
        self.assertSequenceEqual(self.rock.members.all(), [self.bob, self.jane])
        self.assertEqual(
            self.rock.membership_set.filter(
                invite_reason__startswith='Why not?',
            ).count(),
            2,
        )

    def test_add_on_m2m_with_intermediate_model_value_required(self):
        self.rock.nodefaultsnonulls.add(self.jim, through_defaults={'nodefaultnonull': 1})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)

    def test_add_on_m2m_with_intermediate_model_value_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.rock.nodefaultsnonulls.add(self.jim)

    def test_create_on_m2m_with_intermediate_model(self):
        annie = self.rock.members.create(name='Annie', through_defaults={'invite_reason': 'She was just awesome.'})
        self.assertSequenceEqual(self.rock.members.all(), [annie])
        self.assertEqual(self.rock.membership_set.get().invite_reason, 'She was just awesome.')

    def test_create_on_m2m_with_intermediate_model_callable_through_default(self):
        annie = self.rock.members.create(
            name='Annie',
            through_defaults={'invite_reason': lambda: 'She was just awesome.'},
        )
        self.assertSequenceEqual(self.rock.members.all(), [annie])
        self.assertEqual(
            self.rock.membership_set.get().invite_reason,
            'She was just awesome.',
        )

    def test_create_on_m2m_with_intermediate_model_value_required(self):
        self.rock.nodefaultsnonulls.create(name='Test', through_defaults={'nodefaultnonull': 1})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)

    def test_create_on_m2m_with_intermediate_model_value_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.rock.nodefaultsnonulls.create(name='Test')

    def test_get_or_create_on_m2m_with_intermediate_model_value_required(self):
        self.rock.nodefaultsnonulls.get_or_create(name='Test', through_defaults={'nodefaultnonull': 1})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)

    def test_get_or_create_on_m2m_with_intermediate_model_value_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.rock.nodefaultsnonulls.get_or_create(name='Test')

    def test_update_or_create_on_m2m_with_intermediate_model_value_required(self):
        self.rock.nodefaultsnonulls.update_or_create(name='Test', through_defaults={'nodefaultnonull': 1})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)

    def test_update_or_create_on_m2m_with_intermediate_model_value_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.rock.nodefaultsnonulls.update_or_create(name='Test')

    def test_remove_on_m2m_with_intermediate_model(self):
        Membership.objects.create(person=self.jim, group=self.rock)
        self.rock.members.remove(self.jim)
        self.assertSequenceEqual(self.rock.members.all(), [])

    def test_remove_on_m2m_with_intermediate_model_multiple(self):
        Membership.objects.create(person=self.jim, group=self.rock, invite_reason='1')
        Membership.objects.create(person=self.jim, group=self.rock, invite_reason='2')
        self.assertSequenceEqual(self.rock.members.all(), [self.jim, self.jim])
        self.rock.members.remove(self.jim)
        self.assertSequenceEqual(self.rock.members.all(), [])

    def test_set_on_m2m_with_intermediate_model(self):
        members = list(Person.objects.filter(name__in=['Bob', 'Jim']))
        self.rock.members.set(members)
        self.assertSequenceEqual(self.rock.members.all(), [self.bob, self.jim])

    def test_set_on_m2m_with_intermediate_model_value_required(self):
        self.rock.nodefaultsnonulls.set([self.jim], through_defaults={'nodefaultnonull': 1})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)
        self.rock.nodefaultsnonulls.set([self.jim], through_defaults={'nodefaultnonull': 2})
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 1)
        self.rock.nodefaultsnonulls.set([self.jim], through_defaults={'nodefaultnonull': 2}, clear=True)
        self.assertEqual(self.rock.testnodefaultsornulls_set.get().nodefaultnonull, 2)

    def test_set_on_m2m_with_intermediate_model_value_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.rock.nodefaultsnonulls.set([self.jim])

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

    def test_add_on_reverse_m2m_with_intermediate_model(self):
        self.bob.group_set.add(self.rock)
        self.assertSequenceEqual(self.bob.group_set.all(), [self.rock])

    def test_create_on_reverse_m2m_with_intermediate_model(self):
        funk = self.bob.group_set.create(name='Funk')
        self.assertSequenceEqual(self.bob.group_set.all(), [funk])

    def test_remove_on_reverse_m2m_with_intermediate_model(self):
        Membership.objects.create(person=self.bob, group=self.rock)
        self.bob.group_set.remove(self.rock)
        self.assertSequenceEqual(self.bob.group_set.all(), [])

    def test_set_on_reverse_m2m_with_intermediate_model(self):
        members = list(Group.objects.filter(name__in=['Rock', 'Roll']))
        self.bob.group_set.set(members)
        self.assertSequenceEqual(self.bob.group_set.all(), [self.rock, self.roll])

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
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        CustomMembership.objects.create(person=self.jim, group=self.rock, date_joined=yesterday)
        CustomMembership.objects.create(person=self.bob, group=self.rock, date_joined=today)
        CustomMembership.objects.create(person=self.jane, group=self.roll, date_joined=yesterday)
        CustomMembership.objects.create(person=self.jim, group=self.roll, date_joined=today)
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
        c = CustomMembership.objects.create(person=self.bob, group=self.rock)
        self.assertSequenceEqual(self.bob.custom_person_related_name.all(), [c])

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

    def test_self_referential_non_symmetrical_both(self):
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

    def test_self_referential_symmetrical(self):
        tony = PersonSelfRefM2M.objects.create(name='Tony')
        chris = PersonSelfRefM2M.objects.create(name='Chris')
        SymmetricalFriendship.objects.create(
            first=tony, second=chris, date_friended=date.today(),
        )
        self.assertSequenceEqual(tony.sym_friends.all(), [chris])
        # Manually created symmetrical m2m relation doesn't add mirror entry
        # automatically.
        self.assertSequenceEqual(chris.sym_friends.all(), [])
        SymmetricalFriendship.objects.create(
            first=chris, second=tony, date_friended=date.today()
        )
        self.assertSequenceEqual(chris.sym_friends.all(), [tony])

    def test_add_on_symmetrical_m2m_with_intermediate_model(self):
        tony = PersonSelfRefM2M.objects.create(name='Tony')
        chris = PersonSelfRefM2M.objects.create(name='Chris')
        date_friended = date(2017, 1, 3)
        tony.sym_friends.add(chris, through_defaults={'date_friended': date_friended})
        self.assertSequenceEqual(tony.sym_friends.all(), [chris])
        self.assertSequenceEqual(chris.sym_friends.all(), [tony])
        friendship = tony.symmetricalfriendship_set.get()
        self.assertEqual(friendship.date_friended, date_friended)

    def test_set_on_symmetrical_m2m_with_intermediate_model(self):
        tony = PersonSelfRefM2M.objects.create(name='Tony')
        chris = PersonSelfRefM2M.objects.create(name='Chris')
        anne = PersonSelfRefM2M.objects.create(name='Anne')
        kate = PersonSelfRefM2M.objects.create(name='Kate')
        date_friended_add = date(2013, 1, 5)
        date_friended_set = date.today()
        tony.sym_friends.add(
            anne, chris,
            through_defaults={'date_friended': date_friended_add},
        )
        tony.sym_friends.set(
            [anne, kate],
            through_defaults={'date_friended': date_friended_set},
        )
        self.assertSequenceEqual(tony.sym_friends.all(), [anne, kate])
        self.assertSequenceEqual(anne.sym_friends.all(), [tony])
        self.assertSequenceEqual(kate.sym_friends.all(), [tony])
        self.assertEqual(
            kate.symmetricalfriendship_set.get().date_friended,
            date_friended_set,
        )
        # Date is preserved.
        self.assertEqual(
            anne.symmetricalfriendship_set.get().date_friended,
            date_friended_add,
        )
        # Recreate relationship.
        tony.sym_friends.set(
            [anne],
            clear=True,
            through_defaults={'date_friended': date_friended_set},
        )
        self.assertSequenceEqual(tony.sym_friends.all(), [anne])
        self.assertSequenceEqual(anne.sym_friends.all(), [tony])
        self.assertEqual(
            anne.symmetricalfriendship_set.get().date_friended,
            date_friended_set,
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
