from django.db.models import Q
from django.http import Http404
from django.shortcuts import aget_list_or_404, aget_object_or_404
from django.test import TestCase

from .models import RelatedModel, SimpleModel


class GetListObjectOr404Test(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s1 = SimpleModel.objects.create(field=0)
        cls.s2 = SimpleModel.objects.create(field=1)
        cls.r1 = RelatedModel.objects.create(simple=cls.s1)

    async def test_aget_object_or_404(self):
        self.assertEqual(await aget_object_or_404(SimpleModel, field=1), self.s2)
        self.assertEqual(await aget_object_or_404(SimpleModel, Q(field=0)), self.s1)
        self.assertEqual(
            await aget_object_or_404(SimpleModel.objects.all(), field=1), self.s2
        )
        self.assertEqual(
            await aget_object_or_404(self.s1.relatedmodel_set, pk=self.r1.pk), self.r1
        )
        # Http404 is returned if the list is empty.
        msg = "No SimpleModel matches the given query."
        with self.assertRaisesMessage(Http404, msg):
            await aget_object_or_404(SimpleModel, field=2)

    async def test_get_list_or_404(self):
        self.assertEqual(await aget_list_or_404(SimpleModel, field=1), [self.s2])
        self.assertEqual(await aget_list_or_404(SimpleModel, Q(field=0)), [self.s1])
        self.assertEqual(
            await aget_list_or_404(SimpleModel.objects.all(), field=1), [self.s2]
        )
        self.assertEqual(
            await aget_list_or_404(self.s1.relatedmodel_set, pk=self.r1.pk), [self.r1]
        )
        # Http404 is returned if the list is empty.
        msg = "No SimpleModel matches the given query."
        with self.assertRaisesMessage(Http404, msg):
            await aget_list_or_404(SimpleModel, field=2)

    async def test_get_object_or_404_bad_class(self):
        msg = (
            "First argument to aget_object_or_404() must be a Model, Manager, or "
            "QuerySet, not 'str'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            await aget_object_or_404("SimpleModel", field=0)

    async def test_get_list_or_404_bad_class(self):
        msg = (
            "First argument to aget_list_or_404() must be a Model, Manager, or "
            "QuerySet, not 'list'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            await aget_list_or_404([SimpleModel], field=1)
