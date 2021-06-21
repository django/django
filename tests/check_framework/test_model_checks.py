from unittest import mock

from django.core import checks
from django.core.checks import Error, Warning
from django.db import models
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import (
    isolate_apps, modify_settings, override_settings, override_system_checks,
)


class EmptyRouter:
    pass


@isolate_apps('check_framework', attr_name='apps')
@override_system_checks([checks.model_checks.check_all_models])
class DuplicateDBTableTests(SimpleTestCase):
    def test_collision_in_same_app(self):
        class Model1(models.Model):
            class Meta:
                db_table = 'test_table'

        class Model2(models.Model):
            class Meta:
                db_table = 'test_table'

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "db_table 'test_table' is used by multiple models: "
                "check_framework.Model1, check_framework.Model2.",
                obj='test_table',
                id='models.E028',
            )
        ])

    @override_settings(DATABASE_ROUTERS=['check_framework.test_model_checks.EmptyRouter'])
    def test_collision_in_same_app_database_routers_installed(self):
        class Model1(models.Model):
            class Meta:
                db_table = 'test_table'

        class Model2(models.Model):
            class Meta:
                db_table = 'test_table'

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Warning(
                "db_table 'test_table' is used by multiple models: "
                "check_framework.Model1, check_framework.Model2.",
                hint=(
                    'You have configured settings.DATABASE_ROUTERS. Verify '
                    'that check_framework.Model1, check_framework.Model2 are '
                    'correctly routed to separate databases.'
                ),
                obj='test_table',
                id='models.W035',
            )
        ])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_collision_across_apps(self, apps):
        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                db_table = 'test_table'

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                db_table = 'test_table'

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [
            Error(
                "db_table 'test_table' is used by multiple models: "
                "basic.Model1, check_framework.Model2.",
                obj='test_table',
                id='models.E028',
            )
        ])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @override_settings(DATABASE_ROUTERS=['check_framework.test_model_checks.EmptyRouter'])
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_collision_across_apps_database_routers_installed(self, apps):
        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                db_table = 'test_table'

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                db_table = 'test_table'

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [
            Warning(
                "db_table 'test_table' is used by multiple models: "
                "basic.Model1, check_framework.Model2.",
                hint=(
                    'You have configured settings.DATABASE_ROUTERS. Verify '
                    'that basic.Model1, check_framework.Model2 are correctly '
                    'routed to separate databases.'
                ),
                obj='test_table',
                id='models.W035',
            )
        ])

    def test_no_collision_for_unmanaged_models(self):
        class Unmanaged(models.Model):
            class Meta:
                db_table = 'test_table'
                managed = False

        class Managed(models.Model):
            class Meta:
                db_table = 'test_table'

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    def test_no_collision_for_proxy_models(self):
        class Model(models.Model):
            class Meta:
                db_table = 'test_table'

        class ProxyModel(Model):
            class Meta:
                proxy = True

        self.assertEqual(Model._meta.db_table, ProxyModel._meta.db_table)
        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])


@isolate_apps('check_framework', attr_name='apps')
@override_system_checks([checks.model_checks.check_all_models])
class IndexNameTests(SimpleTestCase):
    def test_collision_in_same_model(self):
        index = models.Index(fields=['id'], name='foo')

        class Model(models.Model):
            class Meta:
                indexes = [index, index]

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "index name 'foo' is not unique for model check_framework.Model.",
                id='models.E029',
            ),
        ])

    def test_collision_in_different_models(self):
        index = models.Index(fields=['id'], name='foo')

        class Model1(models.Model):
            class Meta:
                indexes = [index]

        class Model2(models.Model):
            class Meta:
                indexes = [index]

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "index name 'foo' is not unique among models: "
                "check_framework.Model1, check_framework.Model2.",
                id='models.E030',
            ),
        ])

    def test_collision_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                indexes = [models.Index(fields=['id'], name='foo')]
                abstract = True

        class Model1(AbstractModel):
            pass

        class Model2(AbstractModel):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "index name 'foo' is not unique among models: "
                "check_framework.Model1, check_framework.Model2.",
                id='models.E030',
            ),
        ])

    def test_no_collision_abstract_model_interpolation(self):
        class AbstractModel(models.Model):
            name = models.CharField(max_length=20)

            class Meta:
                indexes = [models.Index(fields=['name'], name='%(app_label)s_%(class)s_foo')]
                abstract = True

        class Model1(AbstractModel):
            pass

        class Model2(AbstractModel):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_collision_across_apps(self, apps):
        index = models.Index(fields=['id'], name='foo')

        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                indexes = [index]

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                indexes = [index]

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [
            Error(
                "index name 'foo' is not unique among models: basic.Model1, "
                "check_framework.Model2.",
                id='models.E030',
            ),
        ])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_no_collision_across_apps_interpolation(self, apps):
        index = models.Index(fields=['id'], name='%(app_label)s_%(class)s_foo')

        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                constraints = [index]

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                constraints = [index]

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [])


@isolate_apps('check_framework', attr_name='apps')
@override_system_checks([checks.model_checks.check_all_models])
@skipUnlessDBFeature('supports_table_check_constraints')
class ConstraintNameTests(TestCase):
    def test_collision_in_same_model(self):
        class Model(models.Model):
            class Meta:
                constraints = [
                    models.CheckConstraint(check=models.Q(id__gt=0), name='foo'),
                    models.CheckConstraint(check=models.Q(id__lt=100), name='foo'),
                ]

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "constraint name 'foo' is not unique for model "
                "check_framework.Model.",
                id='models.E031',
            ),
        ])

    def test_collision_in_different_models(self):
        constraint = models.CheckConstraint(check=models.Q(id__gt=0), name='foo')

        class Model1(models.Model):
            class Meta:
                constraints = [constraint]

        class Model2(models.Model):
            class Meta:
                constraints = [constraint]

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "constraint name 'foo' is not unique among models: "
                "check_framework.Model1, check_framework.Model2.",
                id='models.E032',
            ),
        ])

    def test_collision_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                constraints = [models.CheckConstraint(check=models.Q(id__gt=0), name='foo')]
                abstract = True

        class Model1(AbstractModel):
            pass

        class Model2(AbstractModel):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Error(
                "constraint name 'foo' is not unique among models: "
                "check_framework.Model1, check_framework.Model2.",
                id='models.E032',
            ),
        ])

    def test_no_collision_abstract_model_interpolation(self):
        class AbstractModel(models.Model):
            class Meta:
                constraints = [
                    models.CheckConstraint(check=models.Q(id__gt=0), name='%(app_label)s_%(class)s_foo'),
                ]
                abstract = True

        class Model1(AbstractModel):
            pass

        class Model2(AbstractModel):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_collision_across_apps(self, apps):
        constraint = models.CheckConstraint(check=models.Q(id__gt=0), name='foo')

        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                constraints = [constraint]

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                constraints = [constraint]

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [
            Error(
                "constraint name 'foo' is not unique among models: "
                "basic.Model1, check_framework.Model2.",
                id='models.E032',
            ),
        ])

    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    @isolate_apps('basic', 'check_framework', kwarg_name='apps')
    def test_no_collision_across_apps_interpolation(self, apps):
        constraint = models.CheckConstraint(check=models.Q(id__gt=0), name='%(app_label)s_%(class)s_foo')

        class Model1(models.Model):
            class Meta:
                app_label = 'basic'
                constraints = [constraint]

        class Model2(models.Model):
            class Meta:
                app_label = 'check_framework'
                constraints = [constraint]

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [])


def mocked_is_overridden(self, setting):
    # Force treating DEFAULT_AUTO_FIELD = 'django.db.models.AutoField' as a not
    # overridden setting.
    return (
        setting != 'DEFAULT_AUTO_FIELD' or
        self.DEFAULT_AUTO_FIELD != 'django.db.models.AutoField'
    )


@mock.patch('django.conf.UserSettingsHolder.is_overridden', mocked_is_overridden)
@override_settings(DEFAULT_AUTO_FIELD='django.db.models.AutoField')
@isolate_apps('check_framework.apps.CheckDefaultPKConfig', attr_name='apps')
@override_system_checks([checks.model_checks.check_all_models])
class ModelDefaultAutoFieldTests(SimpleTestCase):
    msg = (
        "Auto-created primary key used when not defining a primary key type, "
        "by default 'django.db.models.AutoField'."
    )
    hint = (
        "Configure the DEFAULT_AUTO_FIELD setting or the "
        "CheckDefaultPKConfig.default_auto_field attribute to point to a "
        "subclass of AutoField, e.g. 'django.db.models.BigAutoField'."
    )

    def test_auto_created_pk(self):
        class Model(models.Model):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Warning(self.msg, hint=self.hint, obj=Model, id='models.W042'),
        ])

    def test_explicit_inherited_pk(self):
        class Parent(models.Model):
            id = models.AutoField(primary_key=True)

        class Child(Parent):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    def test_skipped_on_model_with_invalid_app_label(self):
        class Model(models.Model):
            class Meta:
                app_label = 'invalid_app_label'

        self.assertEqual(Model.check(), [])

    def test_skipped_on_abstract_model(self):
        class Abstract(models.Model):
            class Meta:
                abstract = True

        # Call .check() because abstract models are not registered.
        self.assertEqual(Abstract.check(), [])

    def test_explicit_inherited_parent_link(self):
        class Parent(models.Model):
            id = models.AutoField(primary_key=True)

        class Child(Parent):
            parent_ptr = models.OneToOneField(Parent, models.CASCADE, parent_link=True)

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    def test_auto_created_inherited_pk(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Warning(self.msg, hint=self.hint, obj=Parent, id='models.W042'),
        ])

    def test_auto_created_inherited_parent_link(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            parent_ptr = models.OneToOneField(Parent, models.CASCADE, parent_link=True)

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [
            Warning(self.msg, hint=self.hint, obj=Parent, id='models.W042'),
        ])

    @override_settings(DEFAULT_AUTO_FIELD='django.db.models.BigAutoField')
    def test_default_auto_field_setting(self):
        class Model(models.Model):
            pass

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    def test_explicit_pk(self):
        class Model(models.Model):
            id = models.BigAutoField(primary_key=True)

        self.assertEqual(checks.run_checks(app_configs=self.apps.get_app_configs()), [])

    @isolate_apps('check_framework.apps.CheckPKConfig', kwarg_name='apps')
    def test_app_default_auto_field(self, apps):
        class ModelWithPkViaAppConfig(models.Model):
            class Meta:
                app_label = 'check_framework.apps.CheckPKConfig'

        self.assertEqual(checks.run_checks(app_configs=apps.get_app_configs()), [])
