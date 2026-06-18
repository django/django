import uuid

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase, override_settings
from django.test.utils import ignore_warnings, isolate_apps
from django.utils.deprecation import RemovedInDjango71Warning


class MyBigAutoField(models.BigAutoField):
    pass


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", uuid.uuid4)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)


@isolate_apps("model_options")
class TestDefaultPK(SimpleTestCase):
    def test_default_value_of_default_auto_field_setting(self):
        """django.conf.global_settings defaults to BigAutoField."""

        class MyModel(models.Model):
            pass

        self.assertIsInstance(MyModel._meta.pk, models.BigAutoField)

    @ignore_warnings(category=RemovedInDjango71Warning)
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.NonexistentAutoField")
    def test_default_auto_field_setting_nonexistent(self):
        msg = (
            "DEFAULT_AUTO_FIELD refers to the module "
            "'django.db.models.NonexistentAutoField' that could not be "
            "imported."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):

            class Model(models.Model):
                pass

    @override_settings(DEFAULT_PK_FIELD="django.db.models.NonexistentField")
    def test_default_pk_field_setting_nonexistent(self):
        msg = (
            "DEFAULT_PK_FIELD refers to the module "
            "'django.db.models.NonexistentField' that could not be imported."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):

            class Model(models.Model):
                pass

    @override_settings(
        DEFAULT_PK_FIELD="model_options.test_default_pk.UUIDPrimaryKeyField"
    )
    def test_default_pk_field_can_use_uuid_field(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, UUIDPrimaryKeyField)
        self.assertEqual(Model._meta.pk.name, "id")
        self.assertTrue(Model._meta.pk.primary_key)
        self.assertFalse(Model._meta.pk.editable)

    @override_settings(DEFAULT_PK_FIELD="django.db.models.Model")
    def test_default_pk_field_setting_non_field(self):
        msg = (
            "Primary key 'django.db.models.Model' referred by "
            "DEFAULT_PK_FIELD must subclass Field."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class Model(models.Model):
                pass

    @isolate_apps("model_options.apps.ModelPKNonexistentConfig")
    def test_app_default_auto_field_nonexistent(self):
        msg = (
            "model_options.apps.ModelPKNonexistentConfig.default_auto_field "
            "refers to the module 'django.db.models.NonexistentAutoField' "
            "that could not be imported."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):

            class Model(models.Model):
                pass

    @ignore_warnings(category=RemovedInDjango71Warning)
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.TextField")
    def test_default_auto_field_setting_non_auto(self):
        msg = (
            "Primary key 'django.db.models.TextField' referred by "
            "DEFAULT_AUTO_FIELD must subclass AutoField."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class Model(models.Model):
                pass

    @isolate_apps("model_options.apps.ModelPKNonAutoConfig")
    def test_app_default_auto_field_non_auto(self):
        msg = (
            "Primary key 'django.db.models.TextField' referred by "
            "model_options.apps.ModelPKNonAutoConfig.default_auto_field must "
            "subclass AutoField."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class Model(models.Model):
                pass

    @ignore_warnings(category=RemovedInDjango71Warning)
    @override_settings(DEFAULT_AUTO_FIELD=None)
    def test_default_auto_field_setting_none(self):
        msg = "DEFAULT_AUTO_FIELD must not be empty."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):

            class Model(models.Model):
                pass

    @isolate_apps("model_options.apps.ModelPKNoneConfig")
    def test_app_default_auto_field_none(self):
        msg = (
            "model_options.apps.ModelPKNoneConfig.default_auto_field must not "
            "be empty."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):

            class Model(models.Model):
                pass

    @ignore_warnings(category=RemovedInDjango71Warning)
    @isolate_apps("model_options.apps.ModelDefaultPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField")
    def test_default_auto_field_setting(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, models.SmallAutoField)

    @ignore_warnings(category=RemovedInDjango71Warning)
    @override_settings(
        DEFAULT_AUTO_FIELD="model_options.test_default_pk.MyBigAutoField"
    )
    def test_default_auto_field_setting_bigautofield_subclass(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, MyBigAutoField)

    @ignore_warnings(category=RemovedInDjango71Warning)
    @isolate_apps("model_options.apps.ModelPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.AutoField")
    def test_app_default_auto_field(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, models.SmallAutoField)

    @ignore_warnings(category=RemovedInDjango71Warning)
    @isolate_apps("model_options.apps.ModelDefaultPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField")
    def test_m2m_default_auto_field_setting(self):
        class M2MModel(models.Model):
            m2m = models.ManyToManyField("self")

        m2m_pk = M2MModel._meta.get_field("m2m").remote_field.through._meta.pk
        self.assertIsInstance(m2m_pk, models.SmallAutoField)

    @ignore_warnings(category=RemovedInDjango71Warning)
    @isolate_apps("model_options.apps.ModelPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.AutoField")
    def test_m2m_app_default_auto_field(self):
        class M2MModel(models.Model):
            m2m = models.ManyToManyField("self")

        m2m_pk = M2MModel._meta.get_field("m2m").remote_field.through._meta.pk
        self.assertIsInstance(m2m_pk, models.SmallAutoField)
