from django.db.models import Q
from django.test import TestCase

from .models import Annotation, Note, Tag


class TestAddRelAliasQueryStrings(TestCase):
    def test_basic(self):
        qs = Annotation.objects.add_rel_alias(
            notes1='notes', notes2='notes'
        ).filter(
            notes1__note='foo', notes1__note__icontains='bar', notes2__note='baz'
        ).filter(
            notes2__note='buz'
        )
        self.assertEqual(str(qs.query).count(' JOIN '), 4)

    def test_unused(self):
        qs = Annotation.objects.add_rel_alias(
            notes1='notes')
        self.assertEqual(str(qs.query).count(' JOIN '), 0)

    def test_promotion(self):
        qs = Annotation.objects.add_rel_alias(
            notes1='notes').filter(notes1__note__isnull=True)
        # There are two joins, and both of them are LEFT OUTER.
        self.assertEqual(str(qs.query).count(' JOIN '), 2)
        self.assertEqual(str(qs.query).count(' LEFT OUTER '), 2)

    def test_double_apply(self):
        qs = Annotation.objects.add_rel_alias(
            notes1='notes', notes2='notes'
        ).filter(
            notes1__note='foo'
        )
        self.assertEqual(str(qs.query), str(qs.query))

    def test_mix_normal_filter(self):
        qs = Annotation.objects.add_rel_alias(
            notes1='notes', notes2='notes'
        ).filter(
            Q(notes1__note='f1'), Q(notes1__note='f2'), Q(notes__note='f3')
        ).filter(Q(notes1__note='f4'), Q(notes__note='f5'), Q(notes__note__contains='f6'))
        # Two joins for notes1 from both filters, and 4 joins for notes filtering.
        self.assertEqual(str(qs.query).count(' JOIN '), 6)


class TestAddRelAliasFunctional(TestCase):
    @classmethod
    def setUpTestData(cls):
        tag = Tag.objects.create(name='t1')
        cls.a1 = Annotation.objects.create(name='a1', tag=tag)
        cls.a2 = Annotation.objects.create(name='a2', tag=tag)
        cls.a3 = Annotation.objects.create(name='a3', tag=tag)
        cls.a4 = Annotation.objects.create(name='a4', tag=tag)
        cls.a5 = Annotation.objects.create(name='a5', tag=tag)
        cls.n1 = Note.objects.create(note='n1', misc='c1')
        cls.n2 = Note.objects.create(note='n2', misc='c2')
        cls.n3 = Note.objects.create(note='n3', misc='c2')
        cls.n4 = Note.objects.create(note='n4', misc='c2')
        cls.a1.notes.add(cls.n1, cls.n2)
        cls.a2.notes.add(cls.n1, cls.n3)
        cls.a3.notes.add(cls.n3, cls.n4)
        cls.a4.notes.add(cls.n2, cls.n4)

    def test_filter_exclude(self):
        base_qs = Annotation.objects.add_rel_alias(
            notes1='notes', notes2='notes'
        ).filter(
            notes1__note='n1', notes2__misc='c2'
        ).order_by('name')
        self.assertQuerysetEqual(base_qs, [self.a1, self.a2], lambda x: x)
        # Has one note with name n1 and another note with both name n2
        # and misc = c2
        qs = base_qs.filter(
            notes2__note='n2'
        )
        self.assertQuerysetEqual(qs, [self.a1], lambda x: x)
        qs = base_qs.exclude(
            notes2__note='n2'
        )
        self.assertQuerysetEqual(qs, [self.a2], lambda x: x)

    def test_exclude_filter(self):
        base_qs = Annotation.objects.add_rel_alias(
            notes1='notes'
        ).add_rel_alias(
            notes2='notes'
        ).filter(
            ~Q(notes1__note='n1', notes2__misc='c2')
        ).order_by('name')
        self.assertQuerysetEqual(base_qs, [self.a3, self.a4, self.a5], lambda x: x)
        qs = base_qs.filter(
            notes1__note='n1'
        )
        self.assertQuerysetEqual(qs, [], lambda x: x)
        qs = base_qs.exclude(
            notes1__note='n1'
        )
        qs = base_qs.filter(
            notes2__note='n3'
        )
        self.assertQuerysetEqual(qs, [self.a3], lambda x: x)
        qs = base_qs.exclude(
            notes2__note='n3'
        )
        with self.assertRaises(Exception):
            list(qs)
