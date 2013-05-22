from __future__ import absolute_import

import copy

from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models.loading import cache
from django.core.management.color import no_style 
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import Article, ArticleRef, Authors, Reviewers, Scientist, ScientistRef

# We can't test the DEFAULT_TABLESPACE and DEFAULT_INDEX_TABLESPACE settings
# because they're evaluated when the model class is defined. As a consequence,
# @override_settings doesn't work, and the tests depend

def sql_for_table(model):
    return '\n'.join(connection.creation.sql_create_model(model, no_style())[0])

def sql_for_index(model):
    return '\n'.join(connection.creation.sql_indexes_for_model(model, no_style()))


class TablespacesTests(TestCase):

    def setUp(self):
        # The unmanaged models need to be removed after the test in order to
        # prevent bad interactions with the flush operation in other tests.
        self.old_app_models = copy.deepcopy(cache.app_models)
        self.old_app_store = copy.deepcopy(cache.app_store)

        for model in Article, Authors, Reviewers, Scientist:
            model._meta.managed = True

    def tearDown(self):
        for model in Article, Authors, Reviewers, Scientist:
            model._meta.managed = False

        cache.app_models = self.old_app_models
        cache.app_store = self.old_app_store
        cache._get_models_cache = {}

    def assertNumContains(self, haystack, needle, count):
        real_count = haystack.count(needle)
        self.assertEqual(real_count, count, "Found %d instances of '%s', "
                "expected %d" % (real_count, needle, count))

    @skipUnlessDBFeature('supports_tablespaces')
    def test_tablespace_for_model(self):
        sql = sql_for_table(Scientist).lower()
        if settings.DEFAULT_INDEX_TABLESPACE:
            # 1 for the table
            self.assertNumContains(sql, 'tbl_tbsp', 1)
            # 1 for the index on the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)
        else:
            # 1 for the table + 1 for the index on the primary key
            self.assertNumContains(sql, 'tbl_tbsp', 2)

    @skipIfDBFeature('supports_tablespaces')
    def test_tablespace_ignored_for_model(self):
        # No tablespace-related SQL
        self.assertEqual(sql_for_table(Scientist),
                         sql_for_table(ScientistRef))

    @skipUnlessDBFeature('supports_tablespaces')
    def test_tablespace_for_indexed_field(self):
        sql = sql_for_table(Article).lower()
        if settings.DEFAULT_INDEX_TABLESPACE:
            # 1 for the table
            self.assertNumContains(sql, 'tbl_tbsp', 1)
            # 1 for the primary key + 1 for the index on code
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 2)
        else:
            # 1 for the table + 1 for the primary key + 1 for the index on code
            self.assertNumContains(sql, 'tbl_tbsp', 3)

        # 1 for the index on reference
        self.assertNumContains(sql, 'idx_tbsp', 1)

    @skipIfDBFeature('supports_tablespaces')
    def test_tablespace_ignored_for_indexed_field(self):
        # No tablespace-related SQL
        self.assertEqual(sql_for_table(Article),
                         sql_for_table(ArticleRef))

    @skipUnlessDBFeature('supports_tablespaces')
    def test_tablespace_for_many_to_many_field(self):
        sql = sql_for_table(Authors).lower()
        # The join table of the ManyToManyField goes to the model's tablespace,
        # and its indexes too, unless DEFAULT_INDEX_TABLESPACE is set.
        if settings.DEFAULT_INDEX_TABLESPACE:
            # 1 for the table
            self.assertNumContains(sql, 'tbl_tbsp', 1)
            # 1 for the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)
        else:
            # 1 for the table + 1 for the index on the primary key
            self.assertNumContains(sql, 'tbl_tbsp', 2)
        self.assertNumContains(sql, 'idx_tbsp', 0)

        sql = sql_for_index(Authors).lower()
        # The ManyToManyField declares no db_tablespace, its indexes go to
        # the model's tablespace, unless DEFAULT_INDEX_TABLESPACE is set.
        if settings.DEFAULT_INDEX_TABLESPACE:
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 2)
        else:
            self.assertNumContains(sql, 'tbl_tbsp', 2)
        self.assertNumContains(sql, 'idx_tbsp', 0)

        sql = sql_for_table(Reviewers).lower()
        # The join table of the ManyToManyField goes to the model's tablespace,
        # and its indexes too, unless DEFAULT_INDEX_TABLESPACE is set.
        if settings.DEFAULT_INDEX_TABLESPACE:
            # 1 for the table
            self.assertNumContains(sql, 'tbl_tbsp', 1)
            # 1 for the primary key
            self.assertNumContains(sql, settings.DEFAULT_INDEX_TABLESPACE, 1)
        else:
            # 1 for the table + 1 for the index on the primary key
            self.assertNumContains(sql, 'tbl_tbsp', 2)
        self.assertNumContains(sql, 'idx_tbsp', 0)

        sql = sql_for_index(Reviewers).lower()
        # The ManyToManyField declares db_tablespace, its indexes go there.
        self.assertNumContains(sql, 'tbl_tbsp', 0)
        self.assertNumContains(sql, 'idx_tbsp', 2)
