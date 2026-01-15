from django.contrib.gis.db import models
from django.db import connection
from django.db.models import Index, Q
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from .models import City


class SchemaIndexesTests(TransactionTestCase):
    available_apps = []
    models = [City]
    get_opclass_query = """
        SELECT opcname, c.relname FROM pg_opclass AS oc
        JOIN pg_index as i on oc.oid = ANY(i.indclass)
        JOIN pg_class as c on c.oid = i.indexrelid
        WHERE c.relname = %s
    """

    def get_indexes(self, table):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, table)
            return {
                name: constraint["columns"]
                for name, constraint in constraints.items()
                if constraint["index"]
            }

    def has_spatial_indexes(self, table):
        if connection.ops.mysql:
            with connection.cursor() as cursor:
                return connection.introspection.supports_spatial_index(cursor, table)
        elif connection.ops.oracle:
            # Spatial indexes in Meta.indexes are not supported by the Oracle
            # backend (see #31252).
            return False
        return True

    def test_using_sql(self):
        if not connection.ops.postgis:
            self.skipTest("This is a PostGIS-specific test.")
        index = Index(fields=["point"])
        editor = connection.schema_editor()
        self.assertIn(
            "%s USING " % editor.quote_name(City._meta.db_table),
            str(index.create_sql(City, editor)),
        )

    @isolate_apps("gis_tests.geoapp")
    def test_namespaced_db_table(self):
        if not connection.ops.postgis:
            self.skipTest("PostGIS-specific test.")

        class SchemaCity(models.Model):
            point = models.PointField()

            class Meta:
                app_label = "geoapp"
                db_table = 'django_schema"."geoapp_schema_city'

        index = Index(fields=["point"])
        editor = connection.schema_editor()
        create_index_sql = str(index.create_sql(SchemaCity, editor))
        self.assertIn(
            "%s USING " % editor.quote_name(SchemaCity._meta.db_table),
            create_index_sql,
        )
        self.assertIn(
            'CREATE INDEX "geoapp_schema_city_point_9ed70651_id" ',
            create_index_sql,
        )

    def test_index_name(self):
        if not self.has_spatial_indexes(City._meta.db_table):
            self.skipTest("Spatial indexes in Meta.indexes are not supported.")
        index_name = "custom_point_index_name"
        index = Index(fields=["point"], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(City, index)
            indexes = self.get_indexes(City._meta.db_table)
            self.assertIn(index_name, indexes)
            self.assertEqual(indexes[index_name], ["point"])
            editor.remove_index(City, index)

    @skipUnlessDBFeature("supports_partial_indexes")
    def test_partial_index(self):
        name = "city_point_partial_on_name_idx"
        index = Index(fields=["point"], name=name, condition=Q(name="Harahetania"))
        with connection.schema_editor() as editor:
            index_sql = str(index.create_sql(City, editor))
            self.assertIn("WHERE %s" % editor.quote_name("name"), index_sql)
            editor.add_index(City, index)
            indexes = self.get_indexes(City._meta.db_table)
            self.assertIn(index.name, indexes)
            editor.remove_index(City, index)

    def test_tablespace(self):
        if not connection.ops.postgis:
            self.skipTest("PostGIS-specific test.")
        index_name = "city_point_partial_tblspce_idx"
        index = Index(
            name=index_name,
            fields=["point"],
            db_tablespace="pg_default",
            condition=Q(name="Harahetania"),
        )
        with connection.schema_editor() as editor:
            editor.add_index(City, index)
            self.assertIn(
                'TABLESPACE "pg_default" ',
                str(index.create_sql(City, editor)),
            )
            editor.remove_index(City, index)

    @skipUnlessDBFeature("supports_covering_indexes")
    def test_covering_index(self):
        index_name = "city_point_covering_name_idx"
        index = Index(fields=["point"], include=["name"], name=index_name)
        with connection.schema_editor() as editor:
            index_sql = str(index.create_sql(City, editor))
            self.assertIn(
                "(%s) INCLUDE (%s)"
                % (editor.quote_name("point"), editor.quote_name("name")),
                index_sql,
            )
            editor.add_index(City, index)
            indexes = self.get_indexes(City._meta.db_table)
            self.assertIn(index.name, indexes)
            self.assertEqual(indexes[index.name], ["point", "name"])
            editor.remove_index(City, index)

    def test_specified_opclass_is_used(self):
        if not connection.ops.postgis:
            self.skipTest("PostGIS-specific test.")
        index_name = "city_point_geom_3d_idx"
        index = Index(
            fields=["point"], name=index_name, opclasses=["gist_geometry_ops_nd"]
        )
        with connection.schema_editor() as editor, connection.cursor() as cursor:
            editor.add_index(City, index)
            cursor.execute(self.get_opclass_query, [index_name])
            self.assertEqual(cursor.fetchall(), [("gist_geometry_ops_nd", index_name)])
            editor.remove_index(City, index)
