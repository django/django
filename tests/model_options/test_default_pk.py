from django.core.exceptions import ImproperlyConfigured
from django.db import connection, models
from django.test import (
    SimpleTestCase,
    TransactionTestCase,
    override_settings,
)
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import isolate_apps


class MyBigAutoField(models.BigAutoField):
    pass


@isolate_apps("model_options")
class TestDefaultPK(SimpleTestCase):
    def test_default_value_of_default_auto_field_setting(self):
        """django.conf.global_settings defaults to BigAutoField."""

        class MyModel(models.Model):
            pass

        self.assertIsInstance(MyModel._meta.pk, models.BigAutoField)

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

    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.TextField")
    def test_default_auto_field_setting_non_auto(self):
        msg = (
            "Primary key 'django.db.models.TextField' referred by "
            "DEFAULT_AUTO_FIELD must subclass AutoFieldMixin."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class Model(models.Model):
                pass

    @isolate_apps("model_options.apps.ModelPKNonAutoConfig")
    def test_app_default_auto_field_non_auto(self):
        msg = (
            "Primary key 'django.db.models.TextField' referred by "
            "model_options.apps.ModelPKNonAutoConfig.default_auto_field must "
            "subclass AutoFieldMixin."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class Model(models.Model):
                pass

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

    @isolate_apps("model_options.apps.ModelDefaultPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField")
    def test_default_auto_field_setting(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, models.SmallAutoField)

    @override_settings(
        DEFAULT_AUTO_FIELD="model_options.test_default_pk.MyBigAutoField"
    )
    def test_default_auto_field_setting_bigautofield_subclass(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, MyBigAutoField)

    @isolate_apps("model_options.apps.ModelPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.AutoField")
    def test_app_default_auto_field(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, models.SmallAutoField)

    @isolate_apps("model_options.apps.ModelDefaultPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField")
    def test_m2m_default_auto_field_setting(self):
        class M2MModel(models.Model):
            m2m = models.ManyToManyField("self")

        m2m_pk = M2MModel._meta.get_field("m2m").remote_field.through._meta.pk
        self.assertIsInstance(m2m_pk, models.SmallAutoField)

    @isolate_apps("model_options.apps.ModelPKConfig")
    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.AutoField")
    def test_m2m_app_default_auto_field(self):
        class M2MModel(models.Model):
            m2m = models.ManyToManyField("self")

        m2m_pk = M2MModel._meta.get_field("m2m").remote_field.through._meta.pk
        self.assertIsInstance(m2m_pk, models.SmallAutoField)

    @override_settings(DEFAULT_AUTO_FIELD="django.db.models.UUIDAutoField")
    @isolate_apps("model_options")
    def test_default_auto_field_setting_uuid(self):
        class Model(models.Model):
            pass

        self.assertIsInstance(Model._meta.pk, models.UUIDAutoField)


@skipIfDBFeature("requires_literal_defaults")
@skipUnlessDBFeature("supports_uuid4_function")
@override_settings(DEFAULT_AUTO_FIELD="django.db.models.UUIDAutoField")
@isolate_apps("model_options")
class UUIDAutoFieldDatabaseTests(TransactionTestCase):
    available_apps = ["model_options"]

    def test_uuid_autofield_creates_objects(self):
        """Test that UUIDAutoField works with database UUID generation."""

        class Article(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "model_options"

        # Verify the primary key is UUIDAutoField
        self.assertIsInstance(Article._meta.pk, models.UUIDAutoField)

        # Create the table
        connection.disable_constraint_checking()
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(Article)
        finally:
            connection.enable_constraint_checking()

        # Create objects - UUIDs should be generated by database
        article1 = Article.objects.create(title="Article 1")
        article2 = Article.objects.create(title="Article 2")

        # Verify UUIDs are generated
        self.assertIsNotNone(article1.id)
        self.assertIsNotNone(article2.id)
        self.assertNotEqual(article1.id, article2.id)

        # Verify they're UUIDs
        import uuid

        self.assertIsInstance(article1.id, uuid.UUID)
        self.assertIsInstance(article2.id, uuid.UUID)

        # Verify we can retrieve by ID
        retrieved = Article.objects.get(id=article1.id)
        self.assertEqual(retrieved.title, "Article 1")
