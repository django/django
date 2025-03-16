from django.test import TestCase

from .models import DateTimePK, DumbCategory, NamedCategory, ProxyCategory


class ContainsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = DumbCategory.objects.create()
        cls.proxy_category = ProxyCategory.objects.create()

    def test_unsaved_obj(self):
        clone = DateTimePK.objects.create()
        clone.pk = None
        msg = "QuerySet.contains() cannot be used on unsaved objects."
        with self.assertRaisesMessage(ValueError, msg):
            DumbCategory.objects.contains(DumbCategory())
        with self.assertRaisesMessage(ValueError, msg):
            DateTimePK.objects.contains(DateTimePK())
        with self.assertRaisesMessage(ValueError, msg):
            DateTimePK.objects.contains(clone)

    def test_obj_type(self):
        msg = "'obj' must be a model instance."
        with self.assertRaisesMessage(TypeError, msg):
            DumbCategory.objects.contains(object())

    def test_values(self):
        msg = "Cannot call QuerySet.contains() after .values() or .values_list()."
        with self.assertRaisesMessage(TypeError, msg):
            DumbCategory.objects.values_list("pk").contains(self.category)
        with self.assertRaisesMessage(TypeError, msg):
            DumbCategory.objects.values("pk").contains(self.category)

    def test_basic(self):
        with self.assertNumQueries(1):
            self.assertIs(DumbCategory.objects.contains(self.category), True)
        # QuerySet.contains() doesn't evaluate a queryset.
        with self.assertNumQueries(1):
            self.assertIs(DumbCategory.objects.contains(self.category), True)

    def test_evaluated_queryset(self):
        qs = DumbCategory.objects.all()
        proxy_qs = ProxyCategory.objects.all()
        # Evaluate querysets.
        list(qs)
        list(proxy_qs)
        with self.assertNumQueries(0):
            self.assertIs(qs.contains(self.category), True)
            self.assertIs(qs.contains(self.proxy_category), True)
            self.assertIs(proxy_qs.contains(self.category), True)
            self.assertIs(proxy_qs.contains(self.proxy_category), True)

    def test_proxy_model(self):
        with self.assertNumQueries(1):
            self.assertIs(DumbCategory.objects.contains(self.proxy_category), True)
        with self.assertNumQueries(1):
            self.assertIs(ProxyCategory.objects.contains(self.category), True)

    def test_wrong_model(self):
        qs = DumbCategory.objects.all()
        named_category = NamedCategory(name="category")
        with self.assertNumQueries(0):
            self.assertIs(qs.contains(named_category), False)
        # Evaluate the queryset.
        list(qs)
        with self.assertNumQueries(0):
            self.assertIs(qs.contains(named_category), False)
