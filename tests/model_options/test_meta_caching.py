from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps("model_options")
class ForwardPropertiesCachingTests(SimpleTestCase):
    """Tests FORWARD_PROPERTIES for Django's model metadata caching system."""

    def test_fields_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            number = models.IntegerField()

        meta = TestModel._meta

        # Access fields to cache them
        _ = meta.fields
        self.assertIn("fields", meta.__dict__)

        field_names = [field.name for field in meta.__dict__["fields"]]
        self.assertIn("name", field_names)
        self.assertIn("number", field_names)

        TestModel.add_to_class("new_field", models.CharField(max_length=100))

        # Verify the cache was expired
        self.assertNotIn("fields", meta.__dict__)

        meta = TestModel._meta

        self.assertIn("new_field", [field.name for field in meta.fields])
        self.assertIn("fields", meta.__dict__)

    def test_many_to_many_forward_properties(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            parent = models.ForeignKey(
                "self", on_delete=models.CASCADE, null=True, related_name="children"
            )
            tags = models.ManyToManyField("self", related_name="tagged_items")

        meta = TestModel._meta

        # Access many_to_many to cache it
        _ = meta.many_to_many
        self.assertIn("many_to_many", meta.__dict__)

        self.assertIn("tags", [field.name for field in meta.__dict__["many_to_many"]])

        tags_field = TestModel._meta.get_field("tags")
        new_tags_field = models.ManyToManyField(
            "self",
            related_name="new_tagged_items",
            through=tags_field.remote_field.through,
        )

        TestModel.add_to_class("tags", new_tags_field)

        # Verify the cache was expired
        self.assertNotIn("many_to_many", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("tags", [field.name for field in meta.many_to_many])
        self.assertIn("many_to_many", meta.__dict__)

    def test_concrete_fields_caching(self):
        class ParentModel(models.Model):
            parent_field = models.CharField(max_length=100)

        class TestModel(ParentModel):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access concrete_fields to cache it
        _ = meta.concrete_fields
        self.assertIn("concrete_fields", meta.__dict__)

        concrete_field_names = [
            field.name for field in meta.__dict__["concrete_fields"]
        ]
        self.assertIn("parent_field", concrete_field_names)
        self.assertIn("name", concrete_field_names)

        # Create a related model for the ForeignKey
        class RelatedModel(models.Model):
            pass

        TestModel.add_to_class(
            "related", models.ForeignKey(RelatedModel, on_delete=models.CASCADE)
        )

        # Verify the cache was expired
        self.assertNotIn("concrete_fields", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("related", [field.name for field in meta.concrete_fields])
        self.assertIn("concrete_fields", meta.__dict__)

    def test_local_concrete_fields_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            number = models.IntegerField()

        meta = TestModel._meta

        # Access local_concrete_fields to cache it
        _ = meta.local_concrete_fields
        self.assertIn("local_concrete_fields", meta.__dict__)
        self.assertIn(
            "name", [field.name for field in meta.__dict__["local_concrete_fields"]]
        )
        self.assertIn(
            "number", [field.name for field in meta.__dict__["local_concrete_fields"]]
        )

        TestModel.add_to_class("new_field", models.CharField(max_length=100))

        # Verify the cache was expired
        self.assertNotIn("local_concrete_fields", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("new_field", [field.name for field in meta.local_concrete_fields])
        self.assertIn("local_concrete_fields", meta.__dict__)

    def test_non_pk_concrete_field_names_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access _non_pk_concrete_field_names to cache it
        _ = meta._non_pk_concrete_field_names
        self.assertIn("_non_pk_concrete_field_names", meta.__dict__)

        TestModel.add_to_class("new_field", models.CharField(max_length=100))

        # Verify the cache was expired
        self.assertNotIn("_non_pk_concrete_field_names", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("new_field", meta._non_pk_concrete_field_names)
        self.assertIn("_non_pk_concrete_field_names", meta.__dict__)

    def test_reverse_one_to_one_field_names_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        class RelatedModel(models.Model):
            test = models.OneToOneField(TestModel, on_delete=models.CASCADE)

        meta = TestModel._meta

        # Access _reverse_one_to_one_field_names to cache it
        _ = meta._reverse_one_to_one_field_names
        self.assertIn("_reverse_one_to_one_field_names", meta.__dict__)

        class NewRelatedModel(models.Model):
            new_test = models.OneToOneField(TestModel, on_delete=models.CASCADE)

        # Verify the cache was expired
        self.assertNotIn("_reverse_one_to_one_field_names", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("newrelatedmodel", meta._reverse_one_to_one_field_names)
        self.assertIn("_reverse_one_to_one_field_names", meta.__dict__)

    def test_forward_fields_map_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access _forward_fields_map to cache it
        _ = meta._forward_fields_map
        self.assertIn("_forward_fields_map", meta.__dict__)

        TestModel.add_to_class("new_field", models.CharField(max_length=100))

        # Verify the cache was expired
        self.assertNotIn("_forward_fields_map", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("new_field", meta._forward_fields_map)

    def test_managers_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access managers to cache it
        _ = meta.managers
        self.assertIn("managers", meta.__dict__)

        TestModel.add_to_class("custom_manager", models.Manager())

        # Verify the cache was expired
        self.assertNotIn("managers", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("custom_manager", [m.name for m in meta.managers])

    def test_managers_map_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access managers_map to cache it
        _ = meta.managers_map
        self.assertIn("managers_map", meta.__dict__)

        TestModel.add_to_class("custom_manager", models.Manager())
        self.assertNotIn("managers_map", meta.__dict__)

        # Verify the cache was expired
        meta = TestModel._meta
        self.assertIn("custom_manager", meta.managers_map)

    def test_base_manager_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access base_manager to cache it
        _ = meta.base_manager
        self.assertIn("base_manager", meta.__dict__)

        TestModel.add_to_class("custom_manager", models.Manager())

        # Verify the cache was expired
        self.assertNotIn("base_manager", meta.__dict__)

        meta = TestModel._meta
        self.assertIsNotNone(meta.base_manager)

    def test_default_manager_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # Access default_manager to cache it
        _ = meta.default_manager
        self.assertIn("default_manager", meta.__dict__)

        TestModel.add_to_class("custom_manager", models.Manager())

        # Verify the cache was expired
        self.assertNotIn("default_manager", meta.__dict__)

        meta = TestModel._meta
        self.assertIsNotNone(meta.default_manager)

    def test_db_returning_fields_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            number = models.IntegerField()

        meta = TestModel._meta

        # Access db_returning_fields to cache it
        _ = meta.db_returning_fields
        self.assertIn("db_returning_fields", meta.__dict__)

        new_field = models.GeneratedField(
            expression=models.functions.Ord(models.F("initial_field")),
            output_field=models.IntegerField(),
            db_persist=False,
        )
        new_field.name = "new_field"

        # Add a new field
        TestModel._meta.add_field(new_field)

        # Verify the cache was expired
        self.assertNotIn("db_returning_fields", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("new_field", [field.name for field in meta.db_returning_fields])
        self.assertIn("db_returning_fields", meta.__dict__)


@isolate_apps("model_options")
class ReversePropertiesCachingTests(SimpleTestCase):
    """Tests REVERSE_PROPERTIES for Django's model metadata caching system."""

    def test_related_objects_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        class RelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        meta = TestModel._meta

        # Access related_objects to cache it
        _ = meta.related_objects
        self.assertIn("related_objects", meta.__dict__)

        class NewRelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        # Verify the cache was expired
        self.assertNotIn("related_objects", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("relatedmodel", [obj.name for obj in meta.related_objects])
        self.assertIn("newrelatedmodel", [obj.name for obj in meta.related_objects])

    def test_fields_map_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        class RelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        meta = TestModel._meta

        # Access fields_map to cache it
        _ = meta.fields_map
        self.assertIn("fields_map", meta.__dict__)
        self.assertIn("relatedmodel", meta.fields_map)
        self.assertIsInstance(meta.fields_map["relatedmodel"], models.ManyToOneRel)

        class NewRelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        # Verify the cache was expired
        self.assertNotIn("fields_map", meta.__dict__)

        meta = TestModel._meta
        self.assertIn("relatedmodel", meta.fields_map)
        self.assertIn("newrelatedmodel", meta.fields_map)
        self.assertIsInstance(meta.fields_map["relatedmodel"], models.ManyToOneRel)
        self.assertIsInstance(meta.fields_map["newrelatedmodel"], models.ManyToOneRel)

    def test_relation_tree_caching(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        class RelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        meta = TestModel._meta

        # Access _relation_tree to cache it
        _ = meta._relation_tree
        self.assertIn("_relation_tree", meta.__dict__)

        # Verify the relation field is in the tree
        self.assertTrue(
            any(
                field.name == "test" and field.model == RelatedModel
                for field in meta._relation_tree
            )
        )

        class NewRelatedModel(models.Model):
            test = models.ForeignKey(TestModel, on_delete=models.CASCADE)

        # Verify the cache was expired
        self.assertNotIn("_relation_tree", meta.__dict__)

        meta = TestModel._meta
        self.assertTrue(
            any(
                field.name == "test" and field.model == RelatedModel
                for field in meta._relation_tree
            )
        )
        self.assertTrue(
            any(
                field.name == "test" and field.model == NewRelatedModel
                for field in meta._relation_tree
            )
        )
