from __future__ import absolute_import

from django.db import models, IntegrityError
from django.test import TestCase, skipUnlessDBFeature, skipIfDBFeature

from .models import (R, RChild, S, T, U, A, M, MR, MRNull,
    create_a, get_default_r, User, Avatar, HiddenUser, HiddenUserProfile)


class OnDeleteTests(TestCase):
    def setUp(self):
        self.DEFAULT = get_default_r()

    def test_auto(self):
        a = create_a('auto')
        a.auto.delete()
        self.assertFalse(A.objects.filter(name='auto').exists())

    def test_auto_nullable(self):
        a = create_a('auto_nullable')
        a.auto_nullable.delete()
        self.assertFalse(A.objects.filter(name='auto_nullable').exists())

    def test_setvalue(self):
        a = create_a('setvalue')
        a.setvalue.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(self.DEFAULT, a.setvalue)

    def test_setnull(self):
        a = create_a('setnull')
        a.setnull.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(None, a.setnull)

    def test_setdefault(self):
        a = create_a('setdefault')
        a.setdefault.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(self.DEFAULT, a.setdefault)

    def test_setdefault_none(self):
        a = create_a('setdefault_none')
        a.setdefault_none.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(None, a.setdefault_none)

    def test_cascade(self):
        a = create_a('cascade')
        a.cascade.delete()
        self.assertFalse(A.objects.filter(name='cascade').exists())

    def test_cascade_nullable(self):
        a = create_a('cascade_nullable')
        a.cascade_nullable.delete()
        self.assertFalse(A.objects.filter(name='cascade_nullable').exists())

    def test_protect(self):
        a = create_a('protect')
        self.assertRaises(IntegrityError, a.protect.delete)

    def test_do_nothing(self):
        # Testing DO_NOTHING is a bit harder: It would raise IntegrityError for a normal model,
        # so we connect to pre_delete and set the fk to a known value.
        replacement_r = R.objects.create()
        def check_do_nothing(sender, **kwargs):
            obj = kwargs['instance']
            obj.donothing_set.update(donothing=replacement_r)
        models.signals.pre_delete.connect(check_do_nothing)
        a = create_a('do_nothing')
        a.donothing.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(replacement_r, a.donothing)
        models.signals.pre_delete.disconnect(check_do_nothing)

    def test_inheritance_cascade_up(self):
        child = RChild.objects.create()
        child.delete()
        self.assertFalse(R.objects.filter(pk=child.pk).exists())

    def test_inheritance_cascade_down(self):
        child = RChild.objects.create()
        parent = child.r_ptr
        parent.delete()
        self.assertFalse(RChild.objects.filter(pk=child.pk).exists())

    def test_cascade_from_child(self):
        a = create_a('child')
        a.child.delete()
        self.assertFalse(A.objects.filter(name='child').exists())
        self.assertFalse(R.objects.filter(pk=a.child_id).exists())

    def test_cascade_from_parent(self):
        a = create_a('child')
        R.objects.get(pk=a.child_id).delete()
        self.assertFalse(A.objects.filter(name='child').exists())
        self.assertFalse(RChild.objects.filter(pk=a.child_id).exists())

    def test_setnull_from_child(self):
        a = create_a('child_setnull')
        a.child_setnull.delete()
        self.assertFalse(R.objects.filter(pk=a.child_setnull_id).exists())

        a = A.objects.get(pk=a.pk)
        self.assertEqual(None, a.child_setnull)

    def test_setnull_from_parent(self):
        a = create_a('child_setnull')
        R.objects.get(pk=a.child_setnull_id).delete()
        self.assertFalse(RChild.objects.filter(pk=a.child_setnull_id).exists())

        a = A.objects.get(pk=a.pk)
        self.assertEqual(None, a.child_setnull)

    def test_o2o_setnull(self):
        a = create_a('o2o_setnull')
        a.o2o_setnull.delete()
        a = A.objects.get(pk=a.pk)
        self.assertEqual(None, a.o2o_setnull)


class DeletionTests(TestCase):
    def test_m2m(self):
        m = M.objects.create()
        r = R.objects.create()
        MR.objects.create(m=m, r=r)
        r.delete()
        self.assertFalse(MR.objects.exists())

        r = R.objects.create()
        MR.objects.create(m=m, r=r)
        m.delete()
        self.assertFalse(MR.objects.exists())

        m = M.objects.create()
        r = R.objects.create()
        m.m2m.add(r)
        r.delete()
        through = M._meta.get_field('m2m').rel.through
        self.assertFalse(through.objects.exists())

        r = R.objects.create()
        m.m2m.add(r)
        m.delete()
        self.assertFalse(through.objects.exists())

        m = M.objects.create()
        r = R.objects.create()
        MRNull.objects.create(m=m, r=r)
        r.delete()
        self.assertFalse(not MRNull.objects.exists())
        self.assertFalse(m.m2m_through_null.exists())

    def test_bulk(self):
        from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE
        s = S.objects.create(r=R.objects.create())
        for i in xrange(2*GET_ITERATOR_CHUNK_SIZE):
            T.objects.create(s=s)
        #   1 (select related `T` instances)
        # + 1 (select related `U` instances)
        # + 2 (delete `T` instances in batches)
        # + 1 (delete `s`)
        self.assertNumQueries(5, s.delete)
        self.assertFalse(S.objects.exists())

    def test_instance_update(self):
        deleted = []
        related_setnull_sets = []
        def pre_delete(sender, **kwargs):
            obj = kwargs['instance']
            deleted.append(obj)
            if isinstance(obj, R):
                related_setnull_sets.append(list(a.pk for a in obj.setnull_set.all()))

        models.signals.pre_delete.connect(pre_delete)
        a = create_a('update_setnull')
        a.setnull.delete()

        a = create_a('update_cascade')
        a.cascade.delete()

        for obj in deleted:
            self.assertEqual(None, obj.pk)

        for pk_list in related_setnull_sets:
            for a in A.objects.filter(id__in=pk_list):
                self.assertEqual(None, a.setnull)

        models.signals.pre_delete.disconnect(pre_delete)

    def test_deletion_order(self):
        pre_delete_order = []
        post_delete_order = []

        def log_post_delete(sender, **kwargs):
            pre_delete_order.append((sender, kwargs['instance'].pk))

        def log_pre_delete(sender, **kwargs):
            post_delete_order.append((sender, kwargs['instance'].pk))

        models.signals.post_delete.connect(log_post_delete)
        models.signals.pre_delete.connect(log_pre_delete)

        r = R.objects.create(pk=1)
        s1 = S.objects.create(pk=1, r=r)
        s2 = S.objects.create(pk=2, r=r)
        t1 = T.objects.create(pk=1, s=s1)
        t2 = T.objects.create(pk=2, s=s2)
        r.delete()
        self.assertEqual(
            pre_delete_order, [(T, 2), (T, 1), (S, 2), (S, 1), (R, 1)]
        )
        self.assertEqual(
            post_delete_order, [(T, 1), (T, 2), (S, 1), (S, 2), (R, 1)]
        )

        models.signals.post_delete.disconnect(log_post_delete)
        models.signals.post_delete.disconnect(log_pre_delete)

    @skipUnlessDBFeature("can_defer_constraint_checks")
    def test_can_defer_constraint_checks(self):
        u = User.objects.create(
            avatar=Avatar.objects.create()
        )
        a = Avatar.objects.get(pk=u.avatar_id)
        # 1 query to find the users for the avatar.
        # 1 query to delete the user
        # 1 query to delete the avatar
        # The important thing is that when we can defer constraint checks there
        # is no need to do an UPDATE on User.avatar to null it out.
        self.assertNumQueries(3, a.delete)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Avatar.objects.exists())

    @skipIfDBFeature("can_defer_constraint_checks")
    def test_cannot_defer_constraint_checks(self):
        u = User.objects.create(
            avatar=Avatar.objects.create()
        )
        a = Avatar.objects.get(pk=u.avatar_id)
        # 1 query to find the users for the avatar.
        # 1 query to delete the user
        # 1 query to null out user.avatar, because we can't defer the constraint
        # 1 query to delete the avatar
        self.assertNumQueries(4, a.delete)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Avatar.objects.exists())

    def test_hidden_related(self):
        r = R.objects.create()
        h = HiddenUser.objects.create(r=r)
        p = HiddenUserProfile.objects.create(user=h)

        r.delete()
        self.assertEqual(HiddenUserProfile.objects.count(), 0)
