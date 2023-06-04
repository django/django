from unittest import mock

from django.contrib.postgres.indexes import (
    BloomIndex,
    BrinIndex,
    BTreeIndex,
    GinIndex,
    GistIndex,
    HashIndex,
    OpClass,
    PostgresIndex,
    SpGistIndex,
)
from django.db import NotSupportedError, connection
from django.db.models import CharField, F, Index, Q
from django.db.models.functions import Cast, Collate, Length, Lower
from django.test import skipUnlessDBFeature
from django.test.utils import register_lookup

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .fields import SearchVector, SearchVectorField
from .models import CharFieldModel, IntegerArrayModel, Scene, TextFieldModel


class IndexTestMixin:
    def test_name_auto_generation(self):
        index = self.index_class(fields=["field"])
        index.set_name_with_model(CharFieldModel)
        self.assertRegex(
            index.name, r"postgres_te_field_[0-9a-f]{6}_%s" % self.index_class.suffix
        )

    def test_deconstruction_no_customization(self):
        index = self.index_class(
            fields=["title"], name="test_title_%s" % self.index_class.suffix
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.indexes.%s" % self.index_class.__name__
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {"fields": ["title"], "name": "test_title_%s" % self.index_class.suffix},
        )

    def test_deconstruction_with_expressions_no_customization(self):
        name = f"test_title_{self.index_class.suffix}"
        index = self.index_class(Lower("title"), name=name)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(
            path,
            f"django.contrib.postgres.indexes.{self.index_class.__name__}",
        )
        self.assertEqual(args, (Lower("title"),))
        self.assertEqual(kwargs, {"name": name})


class BloomIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = BloomIndex

    def test_suffix(self):
        self.assertEqual(BloomIndex.suffix, "bloom")

    def test_deconstruction(self):
        index = BloomIndex(fields=["title"], name="test_bloom", length=80, columns=[4])
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.BloomIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "test_bloom",
                "length": 80,
                "columns": [4],
            },
        )

    def test_invalid_fields(self):
        msg = "Bloom indexes support a maximum of 32 fields."
        with self.assertRaisesMessage(ValueError, msg):
            BloomIndex(fields=["title"] * 33, name="test_bloom")

    def test_invalid_columns(self):
        msg = "BloomIndex.columns must be a list or tuple."
        with self.assertRaisesMessage(ValueError, msg):
            BloomIndex(fields=["title"], name="test_bloom", columns="x")
        msg = "BloomIndex.columns cannot have more values than fields."
        with self.assertRaisesMessage(ValueError, msg):
            BloomIndex(fields=["title"], name="test_bloom", columns=[4, 3])

    def test_invalid_columns_value(self):
        msg = "BloomIndex.columns must contain integers from 1 to 4095."
        for length in (0, 4096):
            with self.subTest(length), self.assertRaisesMessage(ValueError, msg):
                BloomIndex(fields=["title"], name="test_bloom", columns=[length])

    def test_invalid_length(self):
        msg = "BloomIndex.length must be None or an integer from 1 to 4096."
        for length in (0, 4097):
            with self.subTest(length), self.assertRaisesMessage(ValueError, msg):
                BloomIndex(fields=["title"], name="test_bloom", length=length)


class BrinIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = BrinIndex

    def test_suffix(self):
        self.assertEqual(BrinIndex.suffix, "brin")

    def test_deconstruction(self):
        index = BrinIndex(
            fields=["title"],
            name="test_title_brin",
            autosummarize=True,
            pages_per_range=16,
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.BrinIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "test_title_brin",
                "autosummarize": True,
                "pages_per_range": 16,
            },
        )

    def test_invalid_pages_per_range(self):
        with self.assertRaisesMessage(
            ValueError, "pages_per_range must be None or a positive integer"
        ):
            BrinIndex(fields=["title"], name="test_title_brin", pages_per_range=0)


class BTreeIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = BTreeIndex

    def test_suffix(self):
        self.assertEqual(BTreeIndex.suffix, "btree")

    def test_deconstruction(self):
        index = BTreeIndex(fields=["title"], name="test_title_btree", fillfactor=80)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.BTreeIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs, {"fields": ["title"], "name": "test_title_btree", "fillfactor": 80}
        )


class GinIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = GinIndex

    def test_suffix(self):
        self.assertEqual(GinIndex.suffix, "gin")

    def test_deconstruction(self):
        index = GinIndex(
            fields=["title"],
            name="test_title_gin",
            fastupdate=True,
            gin_pending_list_limit=128,
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.GinIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "test_title_gin",
                "fastupdate": True,
                "gin_pending_list_limit": 128,
            },
        )


class GistIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = GistIndex

    def test_suffix(self):
        self.assertEqual(GistIndex.suffix, "gist")

    def test_deconstruction(self):
        index = GistIndex(
            fields=["title"], name="test_title_gist", buffering=False, fillfactor=80
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.GistIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "test_title_gist",
                "buffering": False,
                "fillfactor": 80,
            },
        )


class HashIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = HashIndex

    def test_suffix(self):
        self.assertEqual(HashIndex.suffix, "hash")

    def test_deconstruction(self):
        index = HashIndex(fields=["title"], name="test_title_hash", fillfactor=80)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.HashIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs, {"fields": ["title"], "name": "test_title_hash", "fillfactor": 80}
        )


class SpGistIndexTests(IndexTestMixin, PostgreSQLSimpleTestCase):
    index_class = SpGistIndex

    def test_suffix(self):
        self.assertEqual(SpGistIndex.suffix, "spgist")

    def test_deconstruction(self):
        index = SpGistIndex(fields=["title"], name="test_title_spgist", fillfactor=80)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.indexes.SpGistIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs, {"fields": ["title"], "name": "test_title_spgist", "fillfactor": 80}
        )


class SchemaTests(PostgreSQLTestCase):
    get_opclass_query = """
        SELECT opcname, c.relname FROM pg_opclass AS oc
        JOIN pg_index as i on oc.oid = ANY(i.indclass)
        JOIN pg_class as c on c.oid = i.indexrelid
        WHERE c.relname = %s
    """

    def get_constraints(self, table):
        """
        Get the indexes on the table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_gin_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn(
            "field", self.get_constraints(IntegerArrayModel._meta.db_table)
        )
        # Add the index
        index_name = "integer_array_model_field_gin"
        index = GinIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        # Check gin index was added
        self.assertEqual(constraints[index_name]["type"], GinIndex.suffix)
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(IntegerArrayModel._meta.db_table)
        )

    def test_gin_fastupdate(self):
        index_name = "integer_array_gin_fastupdate"
        index = GinIndex(fields=["field"], name=index_name, fastupdate=False)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], "gin")
        self.assertEqual(constraints[index_name]["options"], ["fastupdate=off"])
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(IntegerArrayModel._meta.db_table)
        )

    def test_partial_gin_index(self):
        with register_lookup(CharField, Length):
            index_name = "char_field_gin_partial_idx"
            index = GinIndex(
                fields=["field"], name=index_name, condition=Q(field__length=40)
            )
            with connection.schema_editor() as editor:
                editor.add_index(CharFieldModel, index)
            constraints = self.get_constraints(CharFieldModel._meta.db_table)
            self.assertEqual(constraints[index_name]["type"], "gin")
            with connection.schema_editor() as editor:
                editor.remove_index(CharFieldModel, index)
            self.assertNotIn(
                index_name, self.get_constraints(CharFieldModel._meta.db_table)
            )

    def test_partial_gin_index_with_tablespace(self):
        with register_lookup(CharField, Length):
            index_name = "char_field_gin_partial_idx"
            index = GinIndex(
                fields=["field"],
                name=index_name,
                condition=Q(field__length=40),
                db_tablespace="pg_default",
            )
            with connection.schema_editor() as editor:
                editor.add_index(CharFieldModel, index)
                self.assertIn(
                    'TABLESPACE "pg_default" ',
                    str(index.create_sql(CharFieldModel, editor)),
                )
            constraints = self.get_constraints(CharFieldModel._meta.db_table)
            self.assertEqual(constraints[index_name]["type"], "gin")
            with connection.schema_editor() as editor:
                editor.remove_index(CharFieldModel, index)
            self.assertNotIn(
                index_name, self.get_constraints(CharFieldModel._meta.db_table)
            )

    def test_gin_parameters(self):
        index_name = "integer_array_gin_params"
        index = GinIndex(
            fields=["field"],
            name=index_name,
            fastupdate=True,
            gin_pending_list_limit=64,
            db_tablespace="pg_default",
        )
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
            self.assertIn(
                ") WITH (gin_pending_list_limit = 64, fastupdate = on) TABLESPACE",
                str(index.create_sql(IntegerArrayModel, editor)),
            )
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], "gin")
        self.assertEqual(
            constraints[index_name]["options"],
            ["gin_pending_list_limit=64", "fastupdate=on"],
        )
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(IntegerArrayModel._meta.db_table)
        )

    def test_trigram_op_class_gin_index(self):
        index_name = "trigram_op_class_gin"
        index = GinIndex(OpClass(F("scene"), name="gin_trgm_ops"), name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(Scene, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertCountEqual(cursor.fetchall(), [("gin_trgm_ops", index_name)])
        constraints = self.get_constraints(Scene._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertIn(constraints[index_name]["type"], GinIndex.suffix)
        with connection.schema_editor() as editor:
            editor.remove_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(Scene._meta.db_table))

    def test_cast_search_vector_gin_index(self):
        index_name = "cast_search_vector_gin"
        index = GinIndex(Cast("field", SearchVectorField()), name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
            sql = index.create_sql(TextFieldModel, editor)
        table = TextFieldModel._meta.db_table
        constraints = self.get_constraints(table)
        self.assertIn(index_name, constraints)
        self.assertIn(constraints[index_name]["type"], GinIndex.suffix)
        self.assertIs(sql.references_column(table, "field"), True)
        self.assertIn("::tsvector", str(sql))
        with connection.schema_editor() as editor:
            editor.remove_index(TextFieldModel, index)
        self.assertNotIn(index_name, self.get_constraints(table))

    def test_bloom_index(self):
        index_name = "char_field_model_field_bloom"
        index = BloomIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], BloomIndex.suffix)
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_bloom_parameters(self):
        index_name = "char_field_model_field_bloom_params"
        index = BloomIndex(fields=["field"], name=index_name, length=512, columns=[3])
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], BloomIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["length=512", "col1=3"])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_brin_index(self):
        index_name = "char_field_model_field_brin"
        index = BrinIndex(fields=["field"], name=index_name, pages_per_range=4)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], BrinIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["pages_per_range=4"])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_brin_parameters(self):
        index_name = "char_field_brin_params"
        index = BrinIndex(fields=["field"], name=index_name, autosummarize=True)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], BrinIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["autosummarize=on"])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_btree_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn("field", self.get_constraints(CharFieldModel._meta.db_table))
        # Add the index.
        index_name = "char_field_model_field_btree"
        index = BTreeIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        # The index was added.
        self.assertEqual(constraints[index_name]["type"], BTreeIndex.suffix)
        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_btree_parameters(self):
        index_name = "integer_array_btree_fillfactor"
        index = BTreeIndex(fields=["field"], name=index_name, fillfactor=80)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], BTreeIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["fillfactor=80"])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_gist_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn("field", self.get_constraints(CharFieldModel._meta.db_table))
        # Add the index.
        index_name = "char_field_model_field_gist"
        index = GistIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        # The index was added.
        self.assertEqual(constraints[index_name]["type"], GistIndex.suffix)
        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_gist_parameters(self):
        index_name = "integer_array_gist_buffering"
        index = GistIndex(
            fields=["field"], name=index_name, buffering=True, fillfactor=80
        )
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], GistIndex.suffix)
        self.assertEqual(
            constraints[index_name]["options"], ["buffering=on", "fillfactor=80"]
        )
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_gist_include(self):
        index_name = "scene_gist_include_setting"
        index = GistIndex(name=index_name, fields=["scene"], include=["setting"])
        with connection.schema_editor() as editor:
            editor.add_index(Scene, index)
        constraints = self.get_constraints(Scene._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["type"], GistIndex.suffix)
        self.assertEqual(constraints[index_name]["columns"], ["scene", "setting"])
        with connection.schema_editor() as editor:
            editor.remove_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(Scene._meta.db_table))

    def test_tsvector_op_class_gist_index(self):
        index_name = "tsvector_op_class_gist"
        index = GistIndex(
            OpClass(
                SearchVector("scene", "setting", config="english"),
                name="tsvector_ops",
            ),
            name=index_name,
        )
        with connection.schema_editor() as editor:
            editor.add_index(Scene, index)
            sql = index.create_sql(Scene, editor)
        table = Scene._meta.db_table
        constraints = self.get_constraints(table)
        self.assertIn(index_name, constraints)
        self.assertIn(constraints[index_name]["type"], GistIndex.suffix)
        self.assertIs(sql.references_column(table, "scene"), True)
        self.assertIs(sql.references_column(table, "setting"), True)
        with connection.schema_editor() as editor:
            editor.remove_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(table))

    def test_search_vector(self):
        """SearchVector generates IMMUTABLE SQL in order to be indexable."""
        index_name = "test_search_vector"
        index = Index(SearchVector("id", "scene", config="english"), name=index_name)
        # Indexed function must be IMMUTABLE.
        with connection.schema_editor() as editor:
            editor.add_index(Scene, index)
        constraints = self.get_constraints(Scene._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertIs(constraints[index_name]["index"], True)

        with connection.schema_editor() as editor:
            editor.remove_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(Scene._meta.db_table))

    def test_hash_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn("field", self.get_constraints(CharFieldModel._meta.db_table))
        # Add the index.
        index_name = "char_field_model_field_hash"
        index = HashIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        # The index was added.
        self.assertEqual(constraints[index_name]["type"], HashIndex.suffix)
        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_hash_parameters(self):
        index_name = "integer_array_hash_fillfactor"
        index = HashIndex(fields=["field"], name=index_name, fillfactor=80)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], HashIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["fillfactor=80"])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(CharFieldModel._meta.db_table)
        )

    def test_spgist_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn("field", self.get_constraints(TextFieldModel._meta.db_table))
        # Add the index.
        index_name = "text_field_model_field_spgist"
        index = SpGistIndex(fields=["field"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
        constraints = self.get_constraints(TextFieldModel._meta.db_table)
        # The index was added.
        self.assertEqual(constraints[index_name]["type"], SpGistIndex.suffix)
        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(TextFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(TextFieldModel._meta.db_table)
        )

    def test_spgist_parameters(self):
        index_name = "text_field_model_spgist_fillfactor"
        index = SpGistIndex(fields=["field"], name=index_name, fillfactor=80)
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
        constraints = self.get_constraints(TextFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]["type"], SpGistIndex.suffix)
        self.assertEqual(constraints[index_name]["options"], ["fillfactor=80"])
        with connection.schema_editor() as editor:
            editor.remove_index(TextFieldModel, index)
        self.assertNotIn(
            index_name, self.get_constraints(TextFieldModel._meta.db_table)
        )

    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_spgist_include(self):
        index_name = "scene_spgist_include_setting"
        index = SpGistIndex(name=index_name, fields=["scene"], include=["setting"])
        with connection.schema_editor() as editor:
            editor.add_index(Scene, index)
        constraints = self.get_constraints(Scene._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["type"], SpGistIndex.suffix)
        self.assertEqual(constraints[index_name]["columns"], ["scene", "setting"])
        with connection.schema_editor() as editor:
            editor.remove_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(Scene._meta.db_table))

    def test_spgist_include_not_supported(self):
        index_name = "spgist_include_exception"
        index = SpGistIndex(fields=["scene"], name=index_name, include=["setting"])
        msg = "Covering SP-GiST indexes require PostgreSQL 14+."
        with self.assertRaisesMessage(NotSupportedError, msg):
            with mock.patch(
                "django.db.backends.postgresql.features.DatabaseFeatures."
                "supports_covering_spgist_indexes",
                False,
            ):
                with connection.schema_editor() as editor:
                    editor.add_index(Scene, index)
        self.assertNotIn(index_name, self.get_constraints(Scene._meta.db_table))

    def test_custom_suffix(self):
        class CustomSuffixIndex(PostgresIndex):
            suffix = "sfx"

            def create_sql(self, model, schema_editor, using="gin", **kwargs):
                return super().create_sql(model, schema_editor, using=using, **kwargs)

        index = CustomSuffixIndex(fields=["field"], name="custom_suffix_idx")
        self.assertEqual(index.suffix, "sfx")
        with connection.schema_editor() as editor:
            self.assertIn(
                " USING gin ",
                str(index.create_sql(CharFieldModel, editor)),
            )

    def test_op_class(self):
        index_name = "test_op_class"
        index = Index(
            OpClass(Lower("field"), name="text_pattern_ops"),
            name=index_name,
        )
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertCountEqual(cursor.fetchall(), [("text_pattern_ops", index_name)])

    def test_op_class_descending_collation(self):
        collation = connection.features.test_collations.get("non_default")
        if not collation:
            self.skipTest("This backend does not support case-insensitive collations.")
        index_name = "test_op_class_descending_collation"
        index = Index(
            Collate(
                OpClass(Lower("field"), name="text_pattern_ops").desc(nulls_last=True),
                collation=collation,
            ),
            name=index_name,
        )
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
            self.assertIn(
                "COLLATE %s" % editor.quote_name(collation),
                str(index.create_sql(TextFieldModel, editor)),
            )
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertCountEqual(cursor.fetchall(), [("text_pattern_ops", index_name)])
        table = TextFieldModel._meta.db_table
        constraints = self.get_constraints(table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["orders"], ["DESC"])
        with connection.schema_editor() as editor:
            editor.remove_index(TextFieldModel, index)
        self.assertNotIn(index_name, self.get_constraints(table))

    def test_op_class_descending_partial(self):
        index_name = "test_op_class_descending_partial"
        index = Index(
            OpClass(Lower("field"), name="text_pattern_ops").desc(),
            name=index_name,
            condition=Q(field__contains="China"),
        )
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertCountEqual(cursor.fetchall(), [("text_pattern_ops", index_name)])
        constraints = self.get_constraints(TextFieldModel._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["orders"], ["DESC"])

    def test_op_class_descending_partial_tablespace(self):
        index_name = "test_op_class_descending_partial_tablespace"
        index = Index(
            OpClass(Lower("field").desc(), name="text_pattern_ops"),
            name=index_name,
            condition=Q(field__contains="China"),
            db_tablespace="pg_default",
        )
        with connection.schema_editor() as editor:
            editor.add_index(TextFieldModel, index)
            self.assertIn(
                'TABLESPACE "pg_default" ',
                str(index.create_sql(TextFieldModel, editor)),
            )
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertCountEqual(cursor.fetchall(), [("text_pattern_ops", index_name)])
        constraints = self.get_constraints(TextFieldModel._meta.db_table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["orders"], ["DESC"])
