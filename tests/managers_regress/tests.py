from __future__ import unicode_literals

import warnings

from django.db import models
from django.db.utils import DatabaseError
from django.template import Context, Template
from django.test import TestCase, override_settings, skipUnlessDBFeature
from django.test.utils import isolate_apps
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text

from .models import (
    AbstractBase1, AbstractBase2, AbstractBase3, Child1, Child2, Child3,
    Child4, Child5, Child6, Child7, RelatedModel, RelationModel,
)


class ManagersRegressionTests(TestCase):
    def test_managers(self):
        Child1.objects.create(name='fred', data='a1')
        Child1.objects.create(name='barney', data='a2')
        Child2.objects.create(name='fred', data='b1', value=1)
        Child2.objects.create(name='barney', data='b2', value=42)
        Child3.objects.create(name='fred', data='c1', comment='yes')
        Child3.objects.create(name='barney', data='c2', comment='no')
        Child4.objects.create(name='fred', data='d1')
        Child4.objects.create(name='barney', data='d2')
        Child5.objects.create(name='fred', comment='yes')
        Child5.objects.create(name='barney', comment='no')
        Child6.objects.create(name='fred', data='f1', value=42)
        Child6.objects.create(name='barney', data='f2', value=42)
        Child7.objects.create(name='fred')
        Child7.objects.create(name='barney')

        self.assertQuerysetEqual(Child1.manager1.all(), ["<Child1: a1>"])
        self.assertQuerysetEqual(Child1.manager2.all(), ["<Child1: a2>"])
        self.assertQuerysetEqual(Child1._default_manager.all(), ["<Child1: a1>"])

        self.assertQuerysetEqual(Child2._default_manager.all(), ["<Child2: b1>"])
        self.assertQuerysetEqual(Child2.restricted.all(), ["<Child2: b2>"])

        self.assertQuerysetEqual(Child3._default_manager.all(), ["<Child3: c1>"])
        self.assertQuerysetEqual(Child3.manager1.all(), ["<Child3: c1>"])
        self.assertQuerysetEqual(Child3.manager2.all(), ["<Child3: c2>"])

        # Since Child6 inherits from Child4, the corresponding rows from f1 and
        # f2 also appear here. This is the expected result.
        self.assertQuerysetEqual(Child4._default_manager.order_by('data'), [
            "<Child4: d1>",
            "<Child4: d2>",
            "<Child4: f1>",
            "<Child4: f2>",
        ])
        self.assertQuerysetEqual(Child4.manager1.all(), ["<Child4: d1>", "<Child4: f1>"], ordered=False)
        self.assertQuerysetEqual(Child5._default_manager.all(), ["<Child5: fred>"])
        self.assertQuerysetEqual(Child6._default_manager.all(), ["<Child6: f1>", "<Child6: f2>"], ordered=False)
        self.assertQuerysetEqual(
            Child7._default_manager.order_by('name'),
            ["<Child7: barney>", "<Child7: fred>"]
        )

    def test_abstract_manager(self):
        # Accessing the manager on an abstract model should
        # raise an attribute error with an appropriate message.
        # This error message isn't ideal, but if the model is abstract and
        # a lot of the class instantiation logic isn't invoked; if the
        # manager is implied, then we don't get a hook to install the
        # error-raising manager.
        msg = "type object 'AbstractBase3' has no attribute 'objects'"
        with self.assertRaisesMessage(AttributeError, msg):
            AbstractBase3.objects.all()

    def test_custom_abstract_manager(self):
        # Accessing the manager on an abstract model with an custom
        # manager should raise an attribute error with an appropriate
        # message.
        msg = "Manager isn't available; AbstractBase2 is abstract"
        with self.assertRaisesMessage(AttributeError, msg):
            AbstractBase2.restricted.all()

    def test_explicit_abstract_manager(self):
        # Accessing the manager on an abstract model with an explicit
        # manager should raise an attribute error with an appropriate
        # message.
        msg = "Manager isn't available; AbstractBase1 is abstract"
        with self.assertRaisesMessage(AttributeError, msg):
            AbstractBase1.objects.all()

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    @isolate_apps('managers_regress')
    def test_swappable_manager(self):
        class SwappableModel(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPABLE_MODEL'

        # Accessing the manager on a swappable model should
        # raise an attribute error with a helpful message
        msg = (
            "Manager isn't available; 'managers_regress.SwappableModel' "
            "has been swapped for 'managers_regress.Parent'"
        )
        with self.assertRaisesMessage(AttributeError, msg):
            SwappableModel.objects.all()

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    @isolate_apps('managers_regress')
    def test_custom_swappable_manager(self):
        class SwappableModel(models.Model):
            stuff = models.Manager()

            class Meta:
                swappable = 'TEST_SWAPPABLE_MODEL'

        # Accessing the manager on a swappable model with an
        # explicit manager should raise an attribute error with a
        # helpful message
        msg = (
            "Manager isn't available; 'managers_regress.SwappableModel' "
            "has been swapped for 'managers_regress.Parent'"
        )
        with self.assertRaisesMessage(AttributeError, msg):
            SwappableModel.stuff.all()

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    @isolate_apps('managers_regress')
    def test_explicit_swappable_manager(self):
        class SwappableModel(models.Model):
            objects = models.Manager()

            class Meta:
                swappable = 'TEST_SWAPPABLE_MODEL'

        # Accessing the manager on a swappable model with an
        # explicit manager should raise an attribute error with a
        # helpful message
        msg = (
            "Manager isn't available; 'managers_regress.SwappableModel' "
            "has been swapped for 'managers_regress.Parent'"
        )
        with self.assertRaisesMessage(AttributeError, msg):
            SwappableModel.objects.all()

    def test_regress_3871(self):
        related = RelatedModel.objects.create()

        relation = RelationModel()
        relation.fk = related
        relation.gfk = related
        relation.save()
        relation.m2m.add(related)

        t = Template('{{ related.test_fk.all.0 }}{{ related.test_gfk.all.0 }}{{ related.test_m2m.all.0 }}')

        self.assertEqual(
            t.render(Context({'related': related})),
            ''.join([force_text(relation.pk)] * 3),
        )

    def test_field_can_be_called_exact(self):
        # Make sure related managers core filters don't include an
        # explicit `__exact` lookup that could be interpreted as a
        # reference to a foreign `exact` field. refs #23940.
        related = RelatedModel.objects.create(exact=False)
        relation = related.test_fk.create()
        self.assertEqual(related.test_fk.get(), relation)


@isolate_apps('managers_regress')
class TestManagerInheritance(TestCase):
    def test_implicit_inheritance(self):
        class CustomManager(models.Manager):
            pass

        class AbstractModel(models.Model):
            custom_manager = CustomManager()

            class Meta:
                abstract = True

        class PlainModel(models.Model):
            custom_manager = CustomManager()

        self.assertIsInstance(PlainModel._base_manager, models.Manager)
        self.assertIsInstance(PlainModel._default_manager, CustomManager)

        class ModelWithAbstractParent(AbstractModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(ModelWithAbstractParent._base_manager, models.Manager)
        self.assertIsInstance(ModelWithAbstractParent._default_manager, CustomManager)

        class ProxyModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True
                proxy = True

        self.assertIsInstance(ProxyModel._base_manager, models.Manager)
        self.assertIsInstance(ProxyModel._default_manager, CustomManager)

        class MTIModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(MTIModel._base_manager, models.Manager)
        self.assertIsInstance(MTIModel._default_manager, CustomManager)

    def test_default_manager_inheritance(self):
        class CustomManager(models.Manager):
            pass

        class AbstractModel(models.Model):
            another_manager = models.Manager()
            custom_manager = CustomManager()

            class Meta:
                default_manager_name = 'custom_manager'
                abstract = True

        class PlainModel(models.Model):
            another_manager = models.Manager()
            custom_manager = CustomManager()

            class Meta:
                default_manager_name = 'custom_manager'

        self.assertIsInstance(PlainModel._default_manager, CustomManager)

        class ModelWithAbstractParent(AbstractModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(ModelWithAbstractParent._default_manager, CustomManager)

        class ProxyModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True
                proxy = True

        self.assertIsInstance(ProxyModel._default_manager, CustomManager)

        class MTIModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(MTIModel._default_manager, CustomManager)

    def test_base_manager_inheritance(self):
        class CustomManager(models.Manager):
            pass

        class AbstractModel(models.Model):
            another_manager = models.Manager()
            custom_manager = CustomManager()

            class Meta:
                base_manager_name = 'custom_manager'
                abstract = True

        class PlainModel(models.Model):
            another_manager = models.Manager()
            custom_manager = CustomManager()

            class Meta:
                base_manager_name = 'custom_manager'

        self.assertIsInstance(PlainModel._base_manager, CustomManager)

        class ModelWithAbstractParent(AbstractModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(ModelWithAbstractParent._base_manager, CustomManager)

        class ProxyModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True
                proxy = True

        self.assertIsInstance(ProxyModel._base_manager, CustomManager)

        class MTIModel(PlainModel):
            class Meta:
                manager_inheritance_from_future = True

        self.assertIsInstance(MTIModel._base_manager, CustomManager)

    def test_manager_no_duplicates(self):
        class CustomManager(models.Manager):
            pass

        class AbstractModel(models.Model):
            custom_manager = models.Manager()

            class Meta:
                abstract = True

        class TestModel(AbstractModel):
            custom_manager = CustomManager()

        self.assertEqual(TestModel._meta.managers, (TestModel.custom_manager,))
        self.assertEqual(TestModel._meta.managers_map, {'custom_manager': TestModel.custom_manager})


@isolate_apps('managers_regress')
class TestManagerDeprecations(TestCase):
    @skipUnlessDBFeature('gis_enabled')
    def test_use_for_related_fields_on_geomanager(self):
        from django.contrib.gis.db.models import GeoManager

        class MyModel(models.Model):
            objects = GeoManager()

        # Shouldn't issue any warnings, since GeoManager itself will be
        # deprecated at the same time as use_for_related_fields, there
        # is no point annoying users with this deprecation.
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            MyModel._base_manager
        self.assertEqual(len(warns), 0)

    def test_use_for_related_fields_for_base_manager(self):
        class MyManager(models.Manager):
            use_for_related_fields = True

        class MyModel(models.Model):
            objects = MyManager()

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            MyModel._base_manager
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyModel'.",
        )

        # With the new base_manager_name API there shouldn't be any warnings.
        class MyModel2(models.Model):
            objects = MyManager()

            class Meta:
                base_manager_name = 'objects'

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            MyModel2._base_manager
        self.assertEqual(len(warns), 0)

    def test_use_for_related_fields_for_many_to_one(self):
        # Common objects
        class MyManagerQuerySet(models.QuerySet):
            pass

        class MyLegacyManagerQuerySet(models.QuerySet):
            pass

        class MyManager(models.Manager):
            def get_queryset(self):
                return MyManagerQuerySet(model=self.model, using=self._db, hints=self._hints)

        class MyLegacyManager(models.Manager):
            use_for_related_fields = True

            def get_queryset(self):
                return MyLegacyManagerQuerySet(model=self.model, using=self._db, hints=self._hints)

        # With legacy config there should be a deprecation warning
        class MyRelModel(models.Model):
            objects = MyLegacyManager()

        class MyModel(models.Model):
            fk = models.ForeignKey(MyRelModel, on_delete=models.DO_NOTHING)

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel(fk_id=42).fk
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyRelModel'.",
        )

        # With the new base_manager_name API there shouldn't be any warnings.
        class MyRelModel2(models.Model):
            objects = MyManager()

            class Meta:
                base_manager_name = 'objects'

        class MyModel2(models.Model):
            fk = models.ForeignKey(MyRelModel2, on_delete=models.DO_NOTHING)

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel2(fk_id=42).fk
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 0)

        # When mixing base_manager_name and use_for_related_fields, there
        # should be warnings.
        class MyRelModel3(models.Model):
            my_base_manager = MyManager()
            my_default_manager = MyLegacyManager()

            class Meta:
                base_manager_name = 'my_base_manager'
                default_manager_name = 'my_default_manager'

        class MyModel3(models.Model):
            fk = models.ForeignKey(MyRelModel3, on_delete=models.DO_NOTHING)

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel3(fk_id=42).fk
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyRelModel3'.",
        )
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RemovedInDjango20Warning)
            self.assertIsInstance(MyModel3.fk.get_queryset(), MyLegacyManagerQuerySet)

    def test_use_for_related_fields_for_one_to_one(self):
        # Common objects
        class MyManagerQuerySet(models.QuerySet):
            pass

        class MyLegacyManagerQuerySet(models.QuerySet):
            pass

        class MyManager(models.Manager):
            def get_queryset(self):
                return MyManagerQuerySet(model=self.model, using=self._db, hints=self._hints)

        class MyLegacyManager(models.Manager):
            use_for_related_fields = True

            def get_queryset(self):
                return MyLegacyManagerQuerySet(model=self.model, using=self._db, hints=self._hints)

        # With legacy config there should be a deprecation warning
        class MyRelModel(models.Model):
            objects = MyLegacyManager()

        class MyModel(models.Model):
            o2o = models.OneToOneField(MyRelModel, on_delete=models.DO_NOTHING)
            objects = MyLegacyManager()

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel(o2o_id=42).o2o
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyRelModel'.",
        )

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyRelModel(pk=42).mymodel
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyModel'.",
        )

        # With the new base_manager_name API there shouldn't be any warnings.
        class MyRelModel2(models.Model):
            objects = MyManager()

            class Meta:
                base_manager_name = 'objects'

        class MyModel2(models.Model):
            o2o = models.OneToOneField(MyRelModel2, on_delete=models.DO_NOTHING)
            objects = MyManager()

            class Meta:
                base_manager_name = 'objects'

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel2(o2o_id=42).o2o
            except DatabaseError:
                pass
            try:
                MyRelModel2(pk=42).mymodel2
            except DatabaseError:
                pass
        self.assertEqual(len(warns), 0)

        # When mixing base_manager_name and use_for_related_fields, there
        # should be warnings.
        class MyRelModel3(models.Model):
            my_base_manager = MyManager()
            my_default_manager = MyLegacyManager()

            class Meta:
                base_manager_name = 'my_base_manager'
                default_manager_name = 'my_default_manager'

        class MyModel3(models.Model):
            o2o = models.OneToOneField(MyRelModel3, on_delete=models.DO_NOTHING)

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)
            try:
                MyModel3(o2o_id=42).o2o
            except DatabaseError:
                pass

        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "use_for_related_fields is deprecated, "
            "instead set Meta.base_manager_name on "
            "'managers_regress.MyRelModel3'.",
        )
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RemovedInDjango20Warning)
            self.assertIsInstance(MyModel3.o2o.get_queryset(), MyLegacyManagerQuerySet)

    def test_legacy_objects_is_created(self):
        class ConcreteParentWithoutManager(models.Model):
            pass

        class ConcreteParentWithManager(models.Model):
            default = models.Manager()

        class AbstractParent(models.Model):
            default = models.Manager()

            class Meta:
                abstract = True

        # Shouldn't complain since the inherited manager
        # is basically the same that would have been created.
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)

            class MyModel(ConcreteParentWithoutManager):
                    pass
            self.assertEqual(len(warns), 0)

        # Should create 'objects' (set as default) and warn that
        # it will no longer be the case in the future.
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)

            class MyModel2(ConcreteParentWithManager):
                pass
            self.assertEqual(len(warns), 1)
            self.assertEqual(
                str(warns[0].message),
                "Managers from concrete parents will soon qualify as default "
                "managers. As a result, the 'objects' manager won't be created "
                "(or recreated) automatically anymore on "
                "'managers_regress.MyModel2' and 'default' declared on "
                "'managers_regress.ConcreteParentWithManager' will be promoted "
                "to default manager. You can declare explicitly "
                "`objects = models.Manager()` on 'MyModel2' to keep things the "
                "way they are or you can switch to the new behavior right away "
                "by setting `Meta.manager_inheritance_from_future` to `True`.",
            )

            self.assertIs(MyModel2.objects, MyModel2._default_manager)

        # When there is a local manager we shouldn't get any warning
        # and 'objects' shouldn't be created.
        class MyModel3(ConcreteParentWithManager):
            default = models.Manager()
        self.assertIs(MyModel3.default, MyModel3._default_manager)
        self.assertIsNone(getattr(MyModel3, 'objects', None))

        # When there is an inherited manager we shouldn't get any warning
        # and 'objects' shouldn't be created.
        class MyModel4(AbstractParent, ConcreteParentWithManager):
            pass
        self.assertIs(MyModel4.default, MyModel4._default_manager)
        self.assertIsNone(getattr(MyModel4, 'objects', None))

        # With `manager_inheritance_from_future = True` 'objects'
        # shouldn't be created.
        class MyModel5(ConcreteParentWithManager):
            class Meta:
                manager_inheritance_from_future = True
        self.assertIs(MyModel5.default, MyModel5._default_manager)
        self.assertIsNone(getattr(MyModel5, 'objects', None))

    def test_legacy_default_manager_promotion(self):
        class ConcreteParent(models.Model):
            concrete = models.Manager()

        class AbstractParent(models.Model):
            abstract = models.Manager()

            class Meta:
                abstract = True

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always', RemovedInDjango20Warning)

            class MyModel(ConcreteParent, AbstractParent):
                pass
            self.assertEqual(len(warns), 1)
            self.assertEqual(
                str(warns[0].message),
                "Managers from concrete parents will soon qualify as default "
                "managers if they appear before any other managers in the "
                "MRO. As a result, 'abstract' declared on "
                "'managers_regress.AbstractParent' will no longer be the "
                "default manager for 'managers_regress.MyModel' in favor of "
                "'concrete' declared on 'managers_regress.ConcreteParent'. "
                "You can redeclare 'abstract' on 'MyModel' to keep things the "
                "way they are or you can switch to the new behavior right "
                "away by setting `Meta.manager_inheritance_from_future` to "
                "`True`.",
            )
            self.assertIs(MyModel.abstract, MyModel._default_manager)

        class MyModel2(ConcreteParent, AbstractParent):
            abstract = models.Manager()
        self.assertIs(MyModel2.abstract, MyModel2._default_manager)

        class MyModel3(ConcreteParent, AbstractParent):
            class Meta:
                manager_inheritance_from_future = True
        self.assertIs(MyModel3.concrete, MyModel3._default_manager)
