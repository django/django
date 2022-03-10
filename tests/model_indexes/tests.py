from unittest import mock

from django.conf import settings
from django.db import connection, models
from django.db.models.functions import Lower, Upper
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from .models import Book, ChildModel1, ChildModel2


class SimpleIndexesTests(SimpleTestCase):
    def test_suffix(self):
        self.assertEqual(models.Index.suffix, "idx")

    def test_repr(self):
        index = models.Index(fields=["title"])
        named_index = models.Index(fields=["title"], name="title_idx")
        multi_col_index = models.Index(fields=["title", "author"])
        partial_index = models.Index(
            fields=["title"], name="long_books_idx", condition=models.Q(pages__gt=400)
        )
        covering_index = models.Index(
            fields=["title"],
            name="include_idx",
            include=["author", "pages"],
        )
        opclasses_index = models.Index(
            fields=["headline", "body"],
            name="opclasses_idx",
            opclasses=["varchar_pattern_ops", "text_pattern_ops"],
        )
        func_index = models.Index(Lower("title"), "subtitle", name="book_func_idx")
        tablespace_index = models.Index(
            fields=["title"],
            db_tablespace="idx_tbls",
            name="book_tablespace_idx",
        )
        self.assertEqual(repr(index), "<Index: fields=['title']>")
        self.assertEqual(
            repr(named_index),
            "<Index: fields=['title'] name='title_idx'>",
        )
        self.assertEqual(repr(multi_col_index), "<Index: fields=['title', 'author']>")
        self.assertEqual(
            repr(partial_index),
            "<Index: fields=['title'] name='long_books_idx' "
            "condition=(AND: ('pages__gt', 400))>",
        )
        self.assertEqual(
            repr(covering_index),
            "<Index: fields=['title'] name='include_idx' "
            "include=('author', 'pages')>",
        )
        self.assertEqual(
            repr(opclasses_index),
            "<Index: fields=['headline', 'body'] name='opclasses_idx' "
            "opclasses=['varchar_pattern_ops', 'text_pattern_ops']>",
        )
        self.assertEqual(
            repr(func_index),
            "<Index: expressions=(Lower(F(title)), F(subtitle)) "
            "name='book_func_idx'>",
        )
        self.assertEqual(
            repr(tablespace_index),
            "<Index: fields=['title'] name='book_tablespace_idx' "
            "db_tablespace='idx_tbls'>",
        )

    def test_eq(self):
        index = models.Index(fields=["title"])
        same_index = models.Index(fields=["title"])
        another_index = models.Index(fields=["title", "author"])
        index.model = Book
        same_index.model = Book
        another_index.model = Book
        self.assertEqual(index, same_index)
        self.assertEqual(index, mock.ANY)
        self.assertNotEqual(index, another_index)

    def test_eq_func(self):
        index = models.Index(Lower("title"), models.F("author"), name="book_func_idx")
        same_index = models.Index(Lower("title"), "author", name="book_func_idx")
        another_index = models.Index(Lower("title"), name="book_func_idx")
        self.assertEqual(index, same_index)
        self.assertEqual(index, mock.ANY)
        self.assertNotEqual(index, another_index)

    def test_index_fields_type(self):
        with self.assertRaisesMessage(
            ValueError, "Index.fields must be a list or tuple."
        ):
            models.Index(fields="title")

    def test_index_fields_strings(self):
        msg = "Index.fields must contain only strings with field names."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(fields=[models.F("title")])

    def test_fields_tuple(self):
        self.assertEqual(models.Index(fields=("title",)).fields, ["title"])

    def test_requires_field_or_expression(self):
        msg = "At least one field or expression is required to define an index."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index()

    def test_expressions_and_fields_mutually_exclusive(self):
        msg = "Index.fields and expressions are mutually exclusive."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(Upper("foo"), fields=["field"])

    def test_opclasses_requires_index_name(self):
        with self.assertRaisesMessage(
            ValueError, "An index must be named to use opclasses."
        ):
            models.Index(opclasses=["jsonb_path_ops"])

    def test_opclasses_requires_list_or_tuple(self):
        with self.assertRaisesMessage(
            ValueError, "Index.opclasses must be a list or tuple."
        ):
            models.Index(
                name="test_opclass", fields=["field"], opclasses="jsonb_path_ops"
            )

    def test_opclasses_and_fields_same_length(self):
        msg = "Index.fields and Index.opclasses must have the same number of elements."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(
                name="test_opclass",
                fields=["field", "other"],
                opclasses=["jsonb_path_ops"],
            )

    def test_condition_requires_index_name(self):
        with self.assertRaisesMessage(
            ValueError, "An index must be named to use condition."
        ):
            models.Index(condition=models.Q(pages__gt=400))

    def test_expressions_requires_index_name(self):
        msg = "An index must be named to use expressions."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(Lower("field"))

    def test_expressions_with_opclasses(self):
        msg = (
            "Index.opclasses cannot be used with expressions. Use "
            "django.contrib.postgres.indexes.OpClass() instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(
                Lower("field"),
                name="test_func_opclass",
                opclasses=["jsonb_path_ops"],
            )

    def test_condition_must_be_q(self):
        with self.assertRaisesMessage(
            ValueError, "Index.condition must be a Q instance."
        ):
            models.Index(condition="invalid", name="long_book_idx")

    def test_include_requires_list_or_tuple(self):
        msg = "Index.include must be a list or tuple."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(name="test_include", fields=["field"], include="other")

    def test_include_requires_index_name(self):
        msg = "A covering index must be named."
        with self.assertRaisesMessage(ValueError, msg):
            models.Index(fields=["field"], include=["other"])

    def test_name_auto_generation(self):
        index = models.Index(fields=["author"])
        index.set_name_with_model(Book)
        self.assertEqual(index.name, "model_index_author_0f5565_idx")

        # '-' for DESC columns should be accounted for in the index name.
        index = models.Index(fields=["-author"])
        index.set_name_with_model(Book)
        self.assertEqual(index.name, "model_index_author_708765_idx")

        # fields may be truncated in the name. db_column is used for naming.
        long_field_index = models.Index(fields=["pages"])
        long_field_index.set_name_with_model(Book)
        self.assertEqual(long_field_index.name, "model_index_page_co_69235a_idx")

        # suffix can't be longer than 3 characters.
        long_field_index.suffix = "suff"
        msg = (
            "Index too long for multiple database support. Is self.suffix "
            "longer than 3 characters?"
        )
        with self.assertRaisesMessage(ValueError, msg):
            long_field_index.set_name_with_model(Book)

    @isolate_apps("model_indexes")
    def test_name_auto_generation_with_quoted_db_table(self):
        class QuotedDbTable(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                db_table = '"t_quoted"'

        index = models.Index(fields=["name"])
        index.set_name_with_model(QuotedDbTable)
        self.assertEqual(index.name, "t_quoted_name_e4ed1b_idx")

    def test_deconstruction(self):
        index = models.Index(fields=["title"], db_tablespace="idx_tbls")
        index.set_name_with_model(Book)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.db.models.Index")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "model_index_title_196f42_idx",
                "db_tablespace": "idx_tbls",
            },
        )

    def test_deconstruct_with_condition(self):
        index = models.Index(
            name="big_book_index",
            fields=["title"],
            condition=models.Q(pages__gt=400),
        )
        index.set_name_with_model(Book)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.db.models.Index")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "model_index_title_196f42_idx",
                "condition": models.Q(pages__gt=400),
            },
        )

    def test_deconstruct_with_include(self):
        index = models.Index(
            name="book_include_idx",
            fields=["title"],
            include=["author"],
        )
        index.set_name_with_model(Book)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.db.models.Index")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "fields": ["title"],
                "name": "model_index_title_196f42_idx",
                "include": ("author",),
            },
        )

    def test_deconstruct_with_expressions(self):
        index = models.Index(Upper("title"), name="book_func_idx")
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django.db.models.Index")
        self.assertEqual(args, (Upper("title"),))
        self.assertEqual(kwargs, {"name": "book_func_idx"})

    def test_clone(self):
        index = models.Index(fields=["title"])
        new_index = index.clone()
        self.assertIsNot(index, new_index)
        self.assertEqual(index.fields, new_index.fields)

    def test_clone_with_expressions(self):
        index = models.Index(Upper("title"), name="book_func_idx")
        new_index = index.clone()
        self.assertIsNot(index, new_index)
        self.assertEqual(index.expressions, new_index.expressions)

    def test_name_set(self):
        index_names = [index.name for index in Book._meta.indexes]
        self.assertCountEqual(
            index_names,
            [
                "model_index_title_196f42_idx",
                "model_index_isbn_34f975_idx",
                "model_indexes_book_barcode_idx",
            ],
        )

    def test_abstract_children(self):
        index_names = [index.name for index in ChildModel1._meta.indexes]
        self.assertEqual(
            index_names,
            ["model_index_name_440998_idx", "model_indexes_childmodel1_idx"],
        )
        index_names = [index.name for index in ChildModel2._meta.indexes]
        self.assertEqual(
            index_names,
            ["model_index_name_b6c374_idx", "model_indexes_childmodel2_idx"],
        )


class IndexesTests(TestCase):
    @skipUnlessDBFeature("supports_tablespaces")
    def test_db_tablespace(self):
        editor = connection.schema_editor()
        # Index with db_tablespace attribute.
        for fields in [
            # Field with db_tablespace specified on model.
            ["shortcut"],
            # Field without db_tablespace specified on model.
            ["author"],
            # Multi-column with db_tablespaces specified on model.
            ["shortcut", "isbn"],
            # Multi-column without db_tablespace specified on model.
            ["title", "author"],
        ]:
            with self.subTest(fields=fields):
                index = models.Index(fields=fields, db_tablespace="idx_tbls2")
                self.assertIn(
                    '"idx_tbls2"', str(index.create_sql(Book, editor)).lower()
                )
        # Indexes without db_tablespace attribute.
        for fields in [["author"], ["shortcut", "isbn"], ["title", "author"]]:
            with self.subTest(fields=fields):
                index = models.Index(fields=fields)
                # The DEFAULT_INDEX_TABLESPACE setting can't be tested because
                # it's evaluated when the model class is defined. As a
                # consequence, @override_settings doesn't work.
                if settings.DEFAULT_INDEX_TABLESPACE:
                    self.assertIn(
                        '"%s"' % settings.DEFAULT_INDEX_TABLESPACE,
                        str(index.create_sql(Book, editor)).lower(),
                    )
                else:
                    self.assertNotIn("TABLESPACE", str(index.create_sql(Book, editor)))
        # Field with db_tablespace specified on the model and an index without
        # db_tablespace.
        index = models.Index(fields=["shortcut"])
        self.assertIn('"idx_tbls"', str(index.create_sql(Book, editor)).lower())

    @skipUnlessDBFeature("supports_tablespaces")
    def test_func_with_tablespace(self):
        # Functional index with db_tablespace attribute.
        index = models.Index(
            Lower("shortcut").desc(),
            name="functional_tbls",
            db_tablespace="idx_tbls2",
        )
        with connection.schema_editor() as editor:
            sql = str(index.create_sql(Book, editor))
            self.assertIn(editor.quote_name("idx_tbls2"), sql)
        # Functional index without db_tablespace attribute.
        index = models.Index(Lower("shortcut").desc(), name="functional_no_tbls")
        with connection.schema_editor() as editor:
            sql = str(index.create_sql(Book, editor))
            # The DEFAULT_INDEX_TABLESPACE setting can't be tested because it's
            # evaluated when the model class is defined. As a consequence,
            # @override_settings doesn't work.
            if settings.DEFAULT_INDEX_TABLESPACE:
                self.assertIn(
                    editor.quote_name(settings.DEFAULT_INDEX_TABLESPACE),
                    sql,
                )
            else:
                self.assertNotIn("TABLESPACE", sql)
