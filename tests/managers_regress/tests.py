from __future__ import unicode_literals

from django.apps import apps
from django.db import models
from django.template import Context, Template
from django.test import TestCase, override_settings
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
            "<Child4: f2>"
        ]
        )
        self.assertQuerysetEqual(Child4.manager1.all(), [
            "<Child4: d1>",
            "<Child4: f1>"
        ],
            ordered=False
        )
        self.assertQuerysetEqual(Child5._default_manager.all(), ["<Child5: fred>"])
        self.assertQuerysetEqual(Child6._default_manager.all(), ["<Child6: f1>"])
        self.assertQuerysetEqual(Child7._default_manager.order_by('name'), [
            "<Child7: barney>",
            "<Child7: fred>"
        ]
        )

    def test_abstract_manager(self):
        # Accessing the manager on an abstract model should
        # raise an attribute error with an appropriate message.
        try:
            AbstractBase3.objects.all()
            self.fail('Should raise an AttributeError')
        except AttributeError as e:
            # This error message isn't ideal, but if the model is abstract and
            # a lot of the class instantiation logic isn't invoked; if the
            # manager is implied, then we don't get a hook to install the
            # error-raising manager.
            self.assertEqual(str(e), "type object 'AbstractBase3' has no attribute 'objects'")

    def test_custom_abstract_manager(self):
        # Accessing the manager on an abstract model with an custom
        # manager should raise an attribute error with an appropriate
        # message.
        try:
            AbstractBase2.restricted.all()
            self.fail('Should raise an AttributeError')
        except AttributeError as e:
            self.assertEqual(str(e), "Manager isn't available; AbstractBase2 is abstract")

    def test_explicit_abstract_manager(self):
        # Accessing the manager on an abstract model with an explicit
        # manager should raise an attribute error with an appropriate
        # message.
        try:
            AbstractBase1.objects.all()
            self.fail('Should raise an AttributeError')
        except AttributeError as e:
            self.assertEqual(str(e), "Manager isn't available; AbstractBase1 is abstract")

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    def test_swappable_manager(self):
        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        _old_models = apps.app_configs['managers_regress'].models.copy()

        try:
            class SwappableModel(models.Model):
                class Meta:
                    swappable = 'TEST_SWAPPABLE_MODEL'

            # Accessing the manager on a swappable model should
            # raise an attribute error with a helpful message
            try:
                SwappableModel.objects.all()
                self.fail('Should raise an AttributeError')
            except AttributeError as e:
                self.assertEqual(str(e), "Manager isn't available; SwappableModel has been swapped for 'managers_regress.Parent'")

        finally:
            apps.app_configs['managers_regress'].models = _old_models
            apps.all_models['managers_regress'] = _old_models
            apps.clear_cache()

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    def test_custom_swappable_manager(self):
        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        _old_models = apps.app_configs['managers_regress'].models.copy()

        try:
            class SwappableModel(models.Model):

                stuff = models.Manager()

                class Meta:
                    swappable = 'TEST_SWAPPABLE_MODEL'

            # Accessing the manager on a swappable model with an
            # explicit manager should raise an attribute error with a
            # helpful message
            try:
                SwappableModel.stuff.all()
                self.fail('Should raise an AttributeError')
            except AttributeError as e:
                self.assertEqual(str(e), "Manager isn't available; SwappableModel has been swapped for 'managers_regress.Parent'")

        finally:
            apps.app_configs['managers_regress'].models = _old_models
            apps.all_models['managers_regress'] = _old_models
            apps.clear_cache()

    @override_settings(TEST_SWAPPABLE_MODEL='managers_regress.Parent')
    def test_explicit_swappable_manager(self):
        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        _old_models = apps.app_configs['managers_regress'].models.copy()

        try:
            class SwappableModel(models.Model):

                objects = models.Manager()

                class Meta:
                    swappable = 'TEST_SWAPPABLE_MODEL'

            # Accessing the manager on a swappable model with an
            # explicit manager should raise an attribute error with a
            # helpful message
            try:
                SwappableModel.objects.all()
                self.fail('Should raise an AttributeError')
            except AttributeError as e:
                self.assertEqual(str(e), "Manager isn't available; SwappableModel has been swapped for 'managers_regress.Parent'")

        finally:
            apps.app_configs['managers_regress'].models = _old_models
            apps.all_models['managers_regress'] = _old_models
            apps.clear_cache()

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
