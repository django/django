from django.apps import apps
from django.db import models
from django.test import SimpleTestCase, override_settings
from django.test.utils import isolate_lru_cache


class FieldDeconstructionTests(SimpleTestCase):
    """
    Tests the deconstruct() method on all core fields.
    """

    def test_name(self):
        """
        Tests the outputting of the correct name if assigned one.
        """
        # First try using a "normal" field
        field = models.CharField(max_length=65)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        field.set_attributes_from_name("is_awesome_test")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(name, "is_awesome_test")
        # Now try with a ForeignKey
        field = models.ForeignKey("some_fake.ModelName", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        field.set_attributes_from_name("author")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(name, "author")

    def test_db_tablespace(self):
        field = models.Field()
        _, _, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        # With a DEFAULT_DB_TABLESPACE.
        with self.settings(DEFAULT_DB_TABLESPACE="foo"):
            _, _, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        # With a db_tablespace.
        field = models.Field(db_tablespace="foo")
        _, _, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"db_tablespace": "foo"})
        # With a db_tablespace equal to DEFAULT_DB_TABLESPACE.
        with self.settings(DEFAULT_DB_TABLESPACE="foo"):
            _, _, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"db_tablespace": "foo"})

    def test_auto_field(self):
        field = models.AutoField(primary_key=True)
        field.set_attributes_from_name("id")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.AutoField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"primary_key": True})

    def test_big_integer_field(self):
        field = models.BigIntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.BigIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_boolean_field(self):
        field = models.BooleanField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.BooleanField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.BooleanField(default=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.BooleanField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"default": True})

    def test_char_field(self):
        field = models.CharField(max_length=65)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.CharField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 65})
        field = models.CharField(max_length=65, null=True, blank=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.CharField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 65, "null": True, "blank": True})

    def test_char_field_choices(self):
        field = models.CharField(max_length=1, choices=(("A", "One"), ("B", "Two")))
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.CharField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs, {"choices": [("A", "One"), ("B", "Two")], "max_length": 1}
        )

    def test_csi_field(self):
        field = models.CommaSeparatedIntegerField(max_length=100)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.CommaSeparatedIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 100})

    def test_date_field(self):
        field = models.DateField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DateField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.DateField(auto_now=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DateField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"auto_now": True})

    def test_datetime_field(self):
        field = models.DateTimeField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DateTimeField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.DateTimeField(auto_now_add=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DateTimeField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"auto_now_add": True})
        # Bug #21785
        field = models.DateTimeField(auto_now=True, auto_now_add=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DateTimeField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"auto_now_add": True, "auto_now": True})

    def test_decimal_field(self):
        field = models.DecimalField(max_digits=5, decimal_places=2)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DecimalField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_digits": 5, "decimal_places": 2})

    def test_decimal_field_0_decimal_places(self):
        """
        A DecimalField with decimal_places=0 should work (#22272).
        """
        field = models.DecimalField(max_digits=5, decimal_places=0)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.DecimalField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_digits": 5, "decimal_places": 0})

    def test_email_field(self):
        field = models.EmailField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.EmailField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 254})
        field = models.EmailField(max_length=255)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.EmailField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 255})

    def test_file_field(self):
        field = models.FileField(upload_to="foo/bar")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.FileField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"upload_to": "foo/bar"})
        # Test max_length
        field = models.FileField(upload_to="foo/bar", max_length=200)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.FileField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"upload_to": "foo/bar", "max_length": 200})

    def test_file_path_field(self):
        field = models.FilePathField(match=r".*\.txt$")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.FilePathField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"match": r".*\.txt$"})
        field = models.FilePathField(recursive=True, allow_folders=True, max_length=123)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.FilePathField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs, {"recursive": True, "allow_folders": True, "max_length": 123}
        )

    def test_float_field(self):
        field = models.FloatField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.FloatField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_foreign_key(self):
        # Test basic pointing
        from django.contrib.auth.models import Permission

        field = models.ForeignKey("auth.Permission", models.CASCADE)
        field.remote_field.model = Permission
        field.remote_field.field_name = "id"
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "on_delete": models.CASCADE})
        self.assertFalse(hasattr(kwargs["to"], "setting_name"))
        # Test swap detection for swappable model
        field = models.ForeignKey("auth.User", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user", "on_delete": models.CASCADE})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")
        # Swap detection for lowercase swappable model.
        field = models.ForeignKey("auth.user", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user", "on_delete": models.CASCADE})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")
        # Test nonexistent (for now) model
        field = models.ForeignKey("something.Else", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "something.else", "on_delete": models.CASCADE})
        # Test on_delete
        field = models.ForeignKey("auth.User", models.SET_NULL)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user", "on_delete": models.SET_NULL})
        # Test to_field preservation
        field = models.ForeignKey("auth.Permission", models.CASCADE, to_field="foobar")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "to_field": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test related_name preservation
        field = models.ForeignKey(
            "auth.Permission", models.CASCADE, related_name="foobar"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "related_name": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test related_query_name
        field = models.ForeignKey(
            "auth.Permission", models.CASCADE, related_query_name="foobar"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "related_query_name": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test limit_choices_to
        field = models.ForeignKey(
            "auth.Permission", models.CASCADE, limit_choices_to={"foo": "bar"}
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "limit_choices_to": {"foo": "bar"},
                "on_delete": models.CASCADE,
            },
        )
        # Test unique
        field = models.ForeignKey("auth.Permission", models.CASCADE, unique=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {"to": "auth.permission", "unique": True, "on_delete": models.CASCADE},
        )

    @override_settings(AUTH_USER_MODEL="auth.Permission")
    def test_foreign_key_swapped(self):
        with isolate_lru_cache(apps.get_swappable_settings_name):
            # It doesn't matter that we swapped out user for permission;
            # there's no validation. We just want to check the setting stuff works.
            field = models.ForeignKey("auth.Permission", models.CASCADE)
            name, path, args, kwargs = field.deconstruct()

        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "on_delete": models.CASCADE})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")

        # Model names are case-insensitive.
        with isolate_lru_cache(apps.get_swappable_settings_name):
            # It doesn't matter that we swapped out user for permission;
            # there's no validation. We just want to check the setting stuff
            # works.
            field = models.ForeignKey("auth.permission", models.CASCADE)
            name, path, args, kwargs = field.deconstruct()

        self.assertEqual(path, "django.db.models.ForeignKey")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "on_delete": models.CASCADE})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")

    def test_one_to_one(self):
        # Test basic pointing
        from django.contrib.auth.models import Permission

        field = models.OneToOneField("auth.Permission", models.CASCADE)
        field.remote_field.model = Permission
        field.remote_field.field_name = "id"
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "on_delete": models.CASCADE})
        self.assertFalse(hasattr(kwargs["to"], "setting_name"))
        # Test swap detection for swappable model
        field = models.OneToOneField("auth.User", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user", "on_delete": models.CASCADE})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")
        # Test nonexistent (for now) model
        field = models.OneToOneField("something.Else", models.CASCADE)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "something.else", "on_delete": models.CASCADE})
        # Test on_delete
        field = models.OneToOneField("auth.User", models.SET_NULL)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user", "on_delete": models.SET_NULL})
        # Test to_field
        field = models.OneToOneField(
            "auth.Permission", models.CASCADE, to_field="foobar"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "to_field": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test related_name
        field = models.OneToOneField(
            "auth.Permission", models.CASCADE, related_name="foobar"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "related_name": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test related_query_name
        field = models.OneToOneField(
            "auth.Permission", models.CASCADE, related_query_name="foobar"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "related_query_name": "foobar",
                "on_delete": models.CASCADE,
            },
        )
        # Test limit_choices_to
        field = models.OneToOneField(
            "auth.Permission", models.CASCADE, limit_choices_to={"foo": "bar"}
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "auth.permission",
                "limit_choices_to": {"foo": "bar"},
                "on_delete": models.CASCADE,
            },
        )
        # Test unique
        field = models.OneToOneField("auth.Permission", models.CASCADE, unique=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.OneToOneField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "on_delete": models.CASCADE})

    def test_image_field(self):
        field = models.ImageField(
            upload_to="foo/barness", width_field="width", height_field="height"
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ImageField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "upload_to": "foo/barness",
                "width_field": "width",
                "height_field": "height",
            },
        )

    def test_integer_field(self):
        field = models.IntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.IntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_ip_address_field(self):
        field = models.IPAddressField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.IPAddressField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_generic_ip_address_field(self):
        field = models.GenericIPAddressField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.GenericIPAddressField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.GenericIPAddressField(protocol="IPv6")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.GenericIPAddressField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"protocol": "IPv6"})

    def test_many_to_many_field(self):
        # Test normal
        field = models.ManyToManyField("auth.Permission")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission"})
        self.assertFalse(hasattr(kwargs["to"], "setting_name"))
        # Test swappable
        field = models.ManyToManyField("auth.User")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.user"})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")
        # Test through
        field = models.ManyToManyField("auth.Permission", through="auth.Group")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "through": "auth.Group"})
        # Test custom db_table
        field = models.ManyToManyField("auth.Permission", db_table="custom_table")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission", "db_table": "custom_table"})
        # Test related_name
        field = models.ManyToManyField("auth.Permission", related_name="custom_table")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs, {"to": "auth.permission", "related_name": "custom_table"}
        )
        # Test related_query_name
        field = models.ManyToManyField("auth.Permission", related_query_name="foobar")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs, {"to": "auth.permission", "related_query_name": "foobar"}
        )
        # Test limit_choices_to
        field = models.ManyToManyField(
            "auth.Permission", limit_choices_to={"foo": "bar"}
        )
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs, {"to": "auth.permission", "limit_choices_to": {"foo": "bar"}}
        )

    @override_settings(AUTH_USER_MODEL="auth.Permission")
    def test_many_to_many_field_swapped(self):
        with isolate_lru_cache(apps.get_swappable_settings_name):
            # It doesn't matter that we swapped out user for permission;
            # there's no validation. We just want to check the setting stuff works.
            field = models.ManyToManyField("auth.Permission")
            name, path, args, kwargs = field.deconstruct()

        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"to": "auth.permission"})
        self.assertEqual(kwargs["to"].setting_name, "AUTH_USER_MODEL")

    def test_many_to_many_field_related_name(self):
        class MyModel(models.Model):
            flag = models.BooleanField(default=True)
            m2m = models.ManyToManyField("self")
            m2m_related_name = models.ManyToManyField(
                "self",
                related_query_name="custom_query_name",
                limit_choices_to={"flag": True},
            )

        name, path, args, kwargs = MyModel.m2m.field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        # deconstruct() should not include attributes which were not passed to
        # the field during initialization.
        self.assertEqual(kwargs, {"to": "field_deconstruction.mymodel"})
        # Passed attributes.
        name, path, args, kwargs = MyModel.m2m_related_name.field.deconstruct()
        self.assertEqual(path, "django.db.models.ManyToManyField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {
                "to": "field_deconstruction.mymodel",
                "related_query_name": "custom_query_name",
                "limit_choices_to": {"flag": True},
            },
        )

    def test_positive_integer_field(self):
        field = models.PositiveIntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.PositiveIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_positive_small_integer_field(self):
        field = models.PositiveSmallIntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.PositiveSmallIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_positive_big_integer_field(self):
        field = models.PositiveBigIntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.PositiveBigIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_slug_field(self):
        field = models.SlugField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.SlugField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.SlugField(db_index=False, max_length=231)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.SlugField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"db_index": False, "max_length": 231})

    def test_small_integer_field(self):
        field = models.SmallIntegerField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.SmallIntegerField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_text_field(self):
        field = models.TextField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.TextField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_time_field(self):
        field = models.TimeField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.TimeField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

        field = models.TimeField(auto_now=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"auto_now": True})

        field = models.TimeField(auto_now_add=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"auto_now_add": True})

    def test_url_field(self):
        field = models.URLField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.URLField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.URLField(max_length=231)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.URLField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"max_length": 231})

    def test_binary_field(self):
        field = models.BinaryField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django.db.models.BinaryField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})
        field = models.BinaryField(editable=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"editable": True})
