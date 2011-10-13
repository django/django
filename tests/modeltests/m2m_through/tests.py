from __future__ import absolute_import

from datetime import datetime
from operator import attrgetter

from django.test import TestCase

from .models import (Person, Group, Membership, CustomMembership,
    PersonSelfRefM2M, Friendship)


class M2mThroughTests(TestCase):
    def setUp(self):
        self.bob = Person.objects.create(name='Bob')
        self.jim = Person.objects.create(name='Jim')
        self.jane = Person.objects.create(name='Jane')
        self.rock = Group.objects.create(name='Rock')
        self.roll = Group.objects.create(name='Roll')

    def test_m2m_through(self):
        # We start out by making sure that the Group 'rock' has no members.
        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )
        # To make Jim a member of Group Rock, simply create a Membership object.
        m1 = Membership.objects.create(person=self.jim, group=self.rock)
        # We can do the same for Jane and Rock.
        m2 = Membership.objects.create(person=self.jane, group=self.rock)
        # Let's check to make sure that it worked.  Jane and Jim should be members of Rock.
        self.assertQuerysetEqual(
            self.rock.members.all(), [
                'Jane',
                'Jim'
            ],
            attrgetter("name")
        )
        # Now we can add a bunch more Membership objects to test with.
        m3 = Membership.objects.create(person=self.bob, group=self.roll)
        m4 = Membership.objects.create(person=self.jim, group=self.roll)
        m5 = Membership.objects.create(person=self.jane, group=self.roll)
        # We can get Jim's Group membership as with any ForeignKey.
        self.assertQuerysetEqual(
            self.jim.group_set.all(), [
                'Rock',
                'Roll'
            ],
            attrgetter("name")
        )
        # Querying the intermediary model works like normal.
        self.assertEqual(
            repr(Membership.objects.get(person=self.jane, group=self.rock)),
            '<Membership: Jane is a member of Rock>'
        )
        # It's not only get that works. Filter works like normal as well.
        self.assertQuerysetEqual(
            Membership.objects.filter(person=self.jim), [
                '<Membership: Jim is a member of Rock>',
                '<Membership: Jim is a member of Roll>'
            ]
        )
        self.rock.members.clear()
        # Now there will be no members of Rock.
        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )



    def test_forward_descriptors(self):
        # Due to complications with adding via an intermediary model,
        # the add method is not provided.
        self.assertRaises(AttributeError, lambda: self.rock.members.add(self.bob))
        # Create is also disabled as it suffers from the same problems as add.
        self.assertRaises(AttributeError, lambda: self.rock.members.create(name='Anne'))
        # Remove has similar complications, and is not provided either.
        self.assertRaises(AttributeError, lambda: self.rock.members.remove(self.jim))

        m1 = Membership.objects.create(person=self.jim, group=self.rock)
        m2 = Membership.objects.create(person=self.jane, group=self.rock)

        # Here we back up the list of all members of Rock.
        backup = list(self.rock.members.all())
        # ...and we verify that it has worked.
        self.assertEqual(
            [p.name for p in backup],
            ['Jane', 'Jim']
        )
        # The clear function should still work.
        self.rock.members.clear()
        # Now there will be no members of Rock.
        self.assertQuerysetEqual(
            self.rock.members.all(),
            []
        )

        # Assignment should not work with models specifying a through model for many of
        # the same reasons as adding.
        self.assertRaises(AttributeError, setattr, self.rock, "members", backup)
        # Let's re-save those instances that we've cleared.
        m1.save()
        m2.save()
        # Verifying that those instances were re-saved successfully.
        self.assertQuerysetEqual(
            self.rock.members.all(),[
                'Jane',
                'Jim'
            ],
            attrgetter("name")
        )

    def test_reverse_descriptors(self):
        # Due to complications with adding via an intermediary model,
        # the add method is not provided.
        self.assertRaises(AttributeError, lambda: self.bob.group_set.add(self.rock))
        # Create is also disabled as it suffers from the same problems as add.
        self.assertRaises(AttributeError, lambda: self.bob.group_set.create(name="funk"))
        # Remove has similar complications, and is not provided either.
        self.assertRaises(AttributeError, lambda: self.jim.group_set.remove(self.rock))

        m1 = Membership.objects.create(person=self.jim, group=self.rock)
        m2 = Membership.objects.create(person=self.jim, group=self.roll)

        # Here we back up the list of all of Jim's groups.
        backup = list(self.jim.group_set.all())
        self.assertEqual(
            [g.name for g in backup],
            ['Rock', 'Roll']
        )
        # The clear function should still work.
        self.jim.group_set.clear()
        # Now Jim will be in no groups.
        self.assertQuerysetEqual(
            self.jim.group_set.all(),
            []
        )
        # Assignment should not work with models specifying a through model for many of
        # the same reasons as adding.
        self.assertRaises(AttributeError, setattr, self.jim, "group_set", backup)
        # Let's re-save those instances that we've cleared.

        m1.save()
        m2.save()
        # Verifying that those instances were re-saved successfully.
        self.assertQuerysetEqual(
            self.jim.group_set.all(),[
                'Rock',
                'Roll'
            ],
            attrgetter("name")
        )

    def test_custom_tests(self):
        # Let's see if we can query through our second relationship.
        self.assertQuerysetEqual(
            self.rock.custom_members.all(),
            []
        )
        # We can query in the opposite direction as well.
        self.assertQuerysetEqual(
            self.bob.custom.all(),
            []
        )

        cm1 = CustomMembership.objects.create(person=self.bob, group=self.rock)
        cm2 = CustomMembership.objects.create(person=self.jim, group=self.rock)

        # If we get the number of people in Rock, it should be both Bob and Jim.
        self.assertQuerysetEqual(
            self.rock.custom_members.all(),[
                'Bob',
                'Jim'
            ],
            attrgetter("name")
        )
        # Bob should only be in one custom group.
        self.assertQuerysetEqual(
            self.bob.custom.all(),[
                'Rock'
            ],
            attrgetter("name")
        )
        # Let's make sure our new descriptors don't conflict with the FK related_name.
        self.assertQuerysetEqual(
            self.bob.custom_person_related_name.all(),[
                '<CustomMembership: Bob is a member of Rock>'
            ]
        )

    def test_self_referential_tests(self):
        # Let's first create a person who has no friends.
        tony = PersonSelfRefM2M.objects.create(name="Tony")
        self.assertQuerysetEqual(
            tony.friends.all(),
            []
        )

        chris = PersonSelfRefM2M.objects.create(name="Chris")
        f = Friendship.objects.create(first=tony, second=chris, date_friended=datetime.now())

        # Tony should now show that Chris is his friend.
        self.assertQuerysetEqual(
            tony.friends.all(),[
                'Chris'
            ],
            attrgetter("name")
        )
        # But we haven't established that Chris is Tony's Friend.
        self.assertQuerysetEqual(
            chris.friends.all(),
            []
        )
        f2 = Friendship.objects.create(first=chris, second=tony, date_friended=datetime.now())

        # Having added Chris as a friend, let's make sure that his friend set reflects
        # that addition.
        self.assertQuerysetEqual(
            chris.friends.all(),[
                'Tony'
            ],
            attrgetter("name")
        )

        # Chris gets mad and wants to get rid of all of his friends.
        chris.friends.clear()
        # Now he should not have any more friends.
        self.assertQuerysetEqual(
            chris.friends.all(),
            []
        )
        # Since this isn't a symmetrical relation, Tony's friend link still exists.
        self.assertQuerysetEqual(
            tony.friends.all(),[
                'Chris'
            ],
            attrgetter("name")
        )

    def test_query_tests(self):
        m1 = Membership.objects.create(person=self.jim, group=self.rock)
        m2 = Membership.objects.create(person=self.jane, group=self.rock)
        m3 = Membership.objects.create(person=self.bob, group=self.roll)
        m4 = Membership.objects.create(person=self.jim, group=self.roll)
        m5 = Membership.objects.create(person=self.jane, group=self.roll)

        m2.invite_reason = "She was just awesome."
        m2.date_joined = datetime(2006, 1, 1)
        m2.save()
        m3.date_joined = datetime(2004, 1, 1)
        m3.save()
        m5.date_joined = datetime(2004, 1, 1)
        m5.save()

        # We can query for the related model by using its attribute name (members, in
        # this case).
        self.assertQuerysetEqual(
            Group.objects.filter(members__name='Bob'),[
                'Roll'
            ],
            attrgetter("name")
        )

        # To query through the intermediary model, we specify its model name.
        # In this case, membership.
        self.assertQuerysetEqual(
            Group.objects.filter(membership__invite_reason="She was just awesome."),[
                'Rock'
            ],
            attrgetter("name")
        )

        # If we want to query in the reverse direction by the related model, use its
        # model name (group, in this case).
        self.assertQuerysetEqual(
            Person.objects.filter(group__name="Rock"),[
                'Jane',
                'Jim'
            ],
            attrgetter("name")
        )

        cm1 = CustomMembership.objects.create(person=self.bob, group=self.rock)
        cm2 = CustomMembership.objects.create(person=self.jim, group=self.rock)
        # If the m2m field has specified a related_name, using that will work.
        self.assertQuerysetEqual(
            Person.objects.filter(custom__name="Rock"),[
                'Bob',
                'Jim'
            ],
            attrgetter("name")
        )

        # To query through the intermediary model in the reverse direction, we again
        # specify its model name (membership, in this case).
        self.assertQuerysetEqual(
            Person.objects.filter(membership__invite_reason="She was just awesome."),[
                'Jane'
            ],
            attrgetter("name")
        )

        # Let's see all of the groups that Jane joined after 1 Jan 2005:
        self.assertQuerysetEqual(
            Group.objects.filter(membership__date_joined__gt=datetime(2005, 1, 1), membership__person=self.jane),[
                'Rock'
            ],
            attrgetter("name")
        )

        # Queries also work in the reverse direction: Now let's see all of the people
        # that have joined Rock since 1 Jan 2005:
        self.assertQuerysetEqual(
            Person.objects.filter(membership__date_joined__gt=datetime(2005, 1, 1), membership__group=self.rock),[
                'Jane',
                'Jim'
            ],
            attrgetter("name")
        )

        # Conceivably, queries through membership could return correct, but non-unique
        # querysets.  To demonstrate this, we query for all people who have joined a
        # group after 2004:
        self.assertQuerysetEqual(
            Person.objects.filter(membership__date_joined__gt=datetime(2004, 1, 1)),[
                'Jane',
                'Jim',
                'Jim'
            ],
            attrgetter("name")
        )

        # Jim showed up twice, because he joined two groups ('Rock', and 'Roll'):
        self.assertEqual(
            [(m.person.name, m.group.name) for m in Membership.objects.filter(date_joined__gt=datetime(2004, 1, 1))],
            [(u'Jane', u'Rock'), (u'Jim', u'Rock'), (u'Jim', u'Roll')]
        )
        # QuerySet's distinct() method can correct this problem.
        self.assertQuerysetEqual(
            Person.objects.filter(membership__date_joined__gt=datetime(2004, 1, 1)).distinct(),[
                'Jane',
                'Jim'
            ],
            attrgetter("name")
        )
