from django.conf import settings
from django.db import connection, models
from django.test import TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import isolate_apps


def sql_for_table(model):
    with connection.schema_editor(collect_sql=True) as editor:
        editor.create_model(model)
    return editor.collected_sql[0]


def sql_for_index(model):
    return "\n".join(
        str(sql) for sql in connection.schema_editor()._model_indexes_sql(model)
    )


class TablespacesTests(TransactionTestCase):
    available_apps = ["model_options"]

    def assertNumContains(self, haystack, needle, count):
        real_count = haystack.count(needle)
        self.assertEqual(
            real_count,
            count,
            "Found %d instances of '%s', expected %d" % (real_count, needle, count),
        )

    @skipIfDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_ignored_for_model_and_indexed_field(self):
        tablespace = "tbl_tbsp"

        class Scientist(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                db_tablespace = tablespace

        class Article(models.Model):
            title = models.CharField(max_length=50, unique=True)
            code = models.CharField(
                max_length=50, unique=True, db_tablespace=tablespace
            )
            authors = models.ManyToManyField(
                Scientist, related_name="articles_written_set"
            )
            reviewers = models.ManyToManyField(
                Scientist,
                related_name="articles_reviewed_set",
                db_tablespace=tablespace,
            )

            class Meta:
                db_tablespace = tablespace

        scientist_table_sql = sql_for_table(Scientist)
        scientist_index_sql = sql_for_index(Scientist)
        self.assertNotIn(tablespace, scientist_table_sql)
        self.assertNotIn(tablespace, scientist_index_sql)

        article_table_sql = sql_for_table(Article)
        article_index_sql = sql_for_index(Article)
        self.assertNotIn(tablespace, article_table_sql)
        self.assertNotIn(tablespace, article_index_sql)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_model(self):
        class Scientist(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                db_tablespace = "tbl_tbsp"

        sql = sql_for_table(Scientist).lower()

        # 1 for the table + 1 for the index on the primary key
        self.assertNumContains(sql, "tbl_tbsp", 2)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_model_with_default_index_tablespace(self):
        with self.settings(DEFAULT_INDEX_TABLESPACE="default_index_tbsp"):

            class Scientist(models.Model):
                name = models.CharField(max_length=50)

                class Meta:
                    db_tablespace = "tbl_tbsp"

            sql = sql_for_table(Scientist).lower()

            # 1 for the table
            self.assertNumContains(sql, "tbl_tbsp", 1)
            # 1 for the index on the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_indexed_field(self):
        class Scientist(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                db_tablespace = "tbl_tbsp"

        class Article(models.Model):
            title = models.CharField(max_length=50, unique=True)
            code = models.CharField(
                max_length=50, unique=True, db_tablespace="idx_tbsp"
            )
            authors = models.ManyToManyField(
                Scientist, related_name="articles_written_set"
            )
            reviewers = models.ManyToManyField(
                Scientist,
                related_name="articles_reviewed_set",
                db_tablespace="idx_tbsp",
            )

            class Meta:
                db_tablespace = "tbl_tbsp"

        sql = sql_for_table(Article).lower()

        # 1 for the table + 1 for the primary key + 1 for the index on title
        self.assertNumContains(sql, "tbl_tbsp", 3)
        # 1 for the index on code
        self.assertNumContains(sql, "idx_tbsp", 1)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_indexed_field_with_default_index_tablespace(self):
        with self.settings(DEFAULT_INDEX_TABLESPACE="default_index_tbsp"):

            class Scientist(models.Model):
                name = models.CharField(max_length=50)

                class Meta:
                    db_tablespace = "tbl_tbsp"

            class Article(models.Model):
                title = models.CharField(max_length=50, unique=True)
                code = models.CharField(
                    max_length=50, unique=True, db_tablespace="idx_tbsp"
                )
                authors = models.ManyToManyField(
                    Scientist, related_name="articles_written_set"
                )
                reviewers = models.ManyToManyField(
                    Scientist,
                    related_name="articles_reviewed_set",
                    db_tablespace="idx_tbsp",
                )

                class Meta:
                    db_tablespace = "tbl_tbsp"

            sql = sql_for_table(Article).lower()
            # 1 for the table
            self.assertNumContains(sql, "tbl_tbsp", 1)
            # 1 for the primary key + 1 for the index on title
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 2)
            # 1 for the index on code
            self.assertNumContains(sql, "idx_tbsp", 1)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_many_to_many_field(self):
        class Scientist(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                db_tablespace = "tbl_tbsp"

        class Article(models.Model):
            title = models.CharField(max_length=50, unique=True)
            code = models.CharField(
                max_length=50, unique=True, db_tablespace="idx_tbsp"
            )
            authors = models.ManyToManyField(
                Scientist, related_name="articles_written_set"
            )
            reviewers = models.ManyToManyField(
                Scientist,
                related_name="articles_reviewed_set",
                db_tablespace="idx_tbsp",
            )

            class Meta:
                db_tablespace = "tbl_tbsp"

        Authors = Article._meta.get_field("authors").remote_field.through
        Reviewers = Article._meta.get_field("reviewers").remote_field.through

        sql = sql_for_table(Authors).lower()
        # The join table of the ManyToManyField goes to the model's tablespace,
        # and its indexes too.
        # 1 for the table + 1 for the index on the primary key
        self.assertNumContains(sql, "tbl_tbsp", 2)
        self.assertNumContains(sql, "idx_tbsp", 0)

        sql = sql_for_index(Authors).lower()
        # The ManyToManyField declares no db_tablespace, its indexes go to
        # the model's tablespace, unless DEFAULT_INDEX_TABLESPACE is set.
        self.assertNumContains(sql, "tbl_tbsp", 2)
        self.assertNumContains(sql, "idx_tbsp", 0)

        sql = sql_for_table(Reviewers).lower()
        # The join table of the ManyToManyField goes to the model's tablespace,
        # and its indexes too.
        # 1 for the table + 1 for the index on the primary key
        self.assertNumContains(sql, "tbl_tbsp", 2)
        self.assertNumContains(sql, "idx_tbsp", 0)

        sql = sql_for_index(Reviewers).lower()
        # The ManyToManyField declares db_tablespace, its indexes go there.
        self.assertNumContains(sql, "tbl_tbsp", 0)
        self.assertNumContains(sql, "idx_tbsp", 2)

    @skipUnlessDBFeature("supports_tablespaces")
    @isolate_apps("model_options")
    def test_tablespace_for_many_to_many_field_with_default_index_tablespace(self):
        with self.settings(DEFAULT_INDEX_TABLESPACE="default_index_tbsp"):

            class Scientist(models.Model):
                name = models.CharField(max_length=50)

                class Meta:
                    db_tablespace = "tbl_tbsp"

            class Article(models.Model):
                title = models.CharField(max_length=50, unique=True)
                code = models.CharField(
                    max_length=50, unique=True, db_tablespace="idx_tbsp"
                )
                authors = models.ManyToManyField(
                    Scientist, related_name="articles_written_set"
                )
                reviewers = models.ManyToManyField(
                    Scientist,
                    related_name="articles_reviewed_set",
                    db_tablespace="idx_tbsp",
                )

                class Meta:
                    db_tablespace = "tbl_tbsp"

            Authors = Article._meta.get_field("authors").remote_field.through
            Reviewers = Article._meta.get_field("reviewers").remote_field.through

            sql = sql_for_table(Authors).lower()
            # The join table of the ManyToManyField goes to the model's tablespace,
            # but its indexes go to DEFAULT_INDEX_TABLESPACE since it's set.
            # 1 for the table
            self.assertNumContains(sql, "tbl_tbsp", 1)
            # 1 for the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)
            self.assertNumContains(sql, "idx_tbsp", 0)

            sql = sql_for_index(Authors).lower()
            # The ManyToManyField declares no db_tablespace, so its indexes go
            # to DEFAULT_INDEX_TABLESPACE since it's set.
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 2)
            self.assertNumContains(sql, "idx_tbsp", 0)

            sql = sql_for_table(Reviewers).lower()
            # The join table of the ManyToManyField goes to the model's tablespace,
            # and its indexes go to DEFAULT_INDEX_TABLESPACE since it's set.
            # 1 for the table
            self.assertNumContains(sql, "tbl_tbsp", 1)
            # 1 for the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)
            self.assertNumContains(sql, "idx_tbsp", 0)

            sql = sql_for_index(Reviewers).lower()
            # The ManyToManyField declares db_tablespace, so its indexes go there.
            self.assertNumContains(sql, "tbl_tbsp", 0)
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 0)
            self.assertNumContains(sql, "idx_tbsp", 2)
