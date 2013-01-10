from __future__ import absolute_import

from django.test import TestCase
from django.utils import unittest

from .models import (User, UserProfile, UserStat, UserStatResult, StatDetails,
    AdvancedUserStat, Image, Product, Parent1, Parent2, Child1, Child2, Child3,
    Child4)


class ReverseSelectRelatedTestCase(TestCase):
    def setUp(self):
        user = User.objects.create(username="test")
        userprofile = UserProfile.objects.create(user=user, state="KS",
                                                 city="Lawrence")
        results = UserStatResult.objects.create(results='first results')
        userstat = UserStat.objects.create(user=user, posts=150,
                                           results=results)
        details = StatDetails.objects.create(base_stats=userstat, comments=259)

        user2 = User.objects.create(username="bob")
        results2 = UserStatResult.objects.create(results='moar results')
        advstat = AdvancedUserStat.objects.create(user=user2, posts=200, karma=5,
                                                  results=results2)
        StatDetails.objects.create(base_stats=advstat, comments=250)
        p1 = Parent1(name1="Only Parent1")
        p1.save()
        c1 = Child1(name1="Child1 Parent1", name2="Child1 Parent2", value=1)
        c1.save()
        p2 = Parent2(name2="Child2 Parent2")
        p2.save()
        c2 = Child2(name1="Child2 Parent1", parent2=p2, value=2)
        c2.save()

    def test_basic(self):
        with self.assertNumQueries(1):
            u = User.objects.select_related("userprofile").get(username="test")
            self.assertEqual(u.userprofile.state, "KS")

    def test_follow_next_level(self):
        with self.assertNumQueries(1):
            u = User.objects.select_related("userstat__results").get(username="test")
            self.assertEqual(u.userstat.posts, 150)
            self.assertEqual(u.userstat.results.results, 'first results')

    def test_follow_two(self):
        with self.assertNumQueries(1):
            u = User.objects.select_related("userprofile", "userstat").get(username="test")
            self.assertEqual(u.userprofile.state, "KS")
            self.assertEqual(u.userstat.posts, 150)

    def test_follow_two_next_level(self):
        with self.assertNumQueries(1):
            u = User.objects.select_related("userstat__results", "userstat__statdetails").get(username="test")
            self.assertEqual(u.userstat.results.results, 'first results')
            self.assertEqual(u.userstat.statdetails.comments, 259)

    def test_forward_and_back(self):
        with self.assertNumQueries(1):
            stat = UserStat.objects.select_related("user__userprofile").get(user__username="test")
            self.assertEqual(stat.user.userprofile.state, 'KS')
            self.assertEqual(stat.user.userstat.posts, 150)

    def test_back_and_forward(self):
        with self.assertNumQueries(1):
            u = User.objects.select_related("userstat").get(username="test")
            self.assertEqual(u.userstat.user.username, 'test')

    def test_not_followed_by_default(self):
        with self.assertNumQueries(2):
            u = User.objects.select_related().get(username="test")
            self.assertEqual(u.userstat.posts, 150)

    def test_follow_from_child_class(self):
        with self.assertNumQueries(1):
            stat = AdvancedUserStat.objects.select_related('user', 'statdetails').get(posts=200)
            self.assertEqual(stat.statdetails.comments, 250)
            self.assertEqual(stat.user.username, 'bob')

    def test_follow_inheritance(self):
        with self.assertNumQueries(1):
            stat = UserStat.objects.select_related('user', 'advanceduserstat').get(posts=200)
            self.assertEqual(stat.advanceduserstat.posts, 200)
            self.assertEqual(stat.user.username, 'bob')
            self.assertEqual(stat.advanceduserstat.user.username, 'bob')

    def test_nullable_relation(self):
        im = Image.objects.create(name="imag1")
        p1 = Product.objects.create(name="Django Plushie", image=im)
        p2 = Product.objects.create(name="Talking Django Plushie")

        with self.assertNumQueries(1):
            result = sorted(Product.objects.select_related("image"), key=lambda x: x.name)
            self.assertEqual([p.name for p in result], ["Django Plushie", "Talking Django Plushie"])

            self.assertEqual(p1.image, im)
            # Check for ticket #13839
            self.assertIsNone(p2.image)

    def test_missing_reverse(self):
        """
        Ticket #13839: select_related() should NOT cache None
        for missing objects on a reverse 1-1 relation.
        """
        with self.assertNumQueries(1):
            user = User.objects.select_related('userprofile').get(username='bob')
            with self.assertRaises(UserProfile.DoesNotExist):
                user.userprofile

    def test_nullable_missing_reverse(self):
        """
        Ticket #13839: select_related() should NOT cache None
        for missing objects on a reverse 0-1 relation.
        """
        Image.objects.create(name="imag1")

        with self.assertNumQueries(1):
            image = Image.objects.select_related('product').get()
            with self.assertRaises(Product.DoesNotExist):
                image.product

    def test_parent_only(self):
        with self.assertNumQueries(1):
            p = Parent1.objects.select_related('child1').get(name1="Only Parent1")
        with self.assertNumQueries(0):
            with self.assertRaises(Child1.DoesNotExist):
                p.child1

    def test_multiple_subclass(self):
        with self.assertNumQueries(1):
            p = Parent1.objects.select_related('child1').get(name1="Child1 Parent1")
            self.assertEqual(p.child1.name2, 'Child1 Parent2')

    def test_onetoone_with_subclass(self):
        with self.assertNumQueries(1):
            p = Parent2.objects.select_related('child2').get(name2="Child2 Parent2")
            self.assertEqual(p.child2.name1, 'Child2 Parent1')

    def test_onetoone_with_two_subclasses(self):
        with self.assertNumQueries(1):
            p = Parent2.objects.select_related('child2', "child2__child3").get(name2="Child2 Parent2")
            self.assertEqual(p.child2.name1, 'Child2 Parent1')
            with self.assertRaises(Child3.DoesNotExist):
                p.child2.child3
        p3 = Parent2(name2="Child3 Parent2")
        p3.save()
        c2 = Child3(name1="Child3 Parent1", parent2=p3, value=2, value3=3)
        c2.save()
        with self.assertNumQueries(1):
            p = Parent2.objects.select_related('child2', "child2__child3").get(name2="Child3 Parent2")
            self.assertEqual(p.child2.name1, 'Child3 Parent1')
            self.assertEqual(p.child2.child3.value3, 3)
            self.assertEqual(p.child2.child3.value, p.child2.value)
            self.assertEqual(p.child2.name1, p.child2.child3.name1)

    def test_multiinheritance_two_subclasses(self):
        with self.assertNumQueries(1):
            p = Parent1.objects.select_related('child1', 'child1__child4').get(name1="Child1 Parent1")
            self.assertEqual(p.child1.name2, 'Child1 Parent2')
            self.assertEqual(p.child1.name1, p.name1)
            with self.assertRaises(Child4.DoesNotExist):
                p.child1.child4
        Child4(name1='n1', name2='n2', value=1, value4=4).save()
        with self.assertNumQueries(1):
            p = Parent2.objects.select_related('child1', 'child1__child4').get(name2="n2")
            self.assertEqual(p.name2, 'n2')
            self.assertEqual(p.child1.name1, 'n1')
            self.assertEqual(p.child1.name2, p.name2)
            self.assertEqual(p.child1.value, 1)
            self.assertEqual(p.child1.child4.name1, p.child1.name1)
            self.assertEqual(p.child1.child4.name2, p.child1.name2)
            self.assertEqual(p.child1.child4.value, p.child1.value)
            self.assertEqual(p.child1.child4.value4, 4)

    @unittest.expectedFailure
    def test_inheritance_deferred(self):
        c = Child4.objects.create(name1='n1', name2='n2', value=1, value4=4)
        with self.assertNumQueries(1):
            p = Parent2.objects.select_related('child1').only(
                'id2',  'child1__value').get(name2="n2")
            self.assertEqual(p.id2, c.id2)
            self.assertEqual(p.child1.value, 1)
        p = Parent2.objects.select_related('child1').only(
            'id2',  'child1__value').get(name2="n2")
        with self.assertNumQueries(1):
            self.assertEqual(p.name2, 'n2')
        p = Parent2.objects.select_related('child1').only(
            'id2',  'child1__value').get(name2="n2")
        with self.assertNumQueries(1):
            self.assertEqual(p.child1.name2, 'n2')

    @unittest.expectedFailure
    def test_inheritance_deferred2(self):
        c = Child4.objects.create(name1='n1', name2='n2', value=1, value4=4)
        qs = Parent2.objects.select_related('child1', 'child4').only(
            'id2',  'child1__value', 'child1__child4__value4')
        with self.assertNumQueries(1):
            p = qs.get(name2="n2")
            self.assertEqual(p.id2, c.id2)
            self.assertEqual(p.child1.value, 1)
            self.assertEqual(p.child1.child4.value4, 4)
            self.assertEqual(p.child1.child4.id2, c.id2)
        p = qs.get(name2="n2")
        with self.assertNumQueries(1):
            self.assertEqual(p.child1.name2, 'n2')
        p = qs.get(name2="n2")
        with self.assertNumQueries(1):
            self.assertEqual(p.child1.name1, 'n1')
        with self.assertNumQueries(1):
            self.assertEqual(p.child1.child4.name1, 'n1')
