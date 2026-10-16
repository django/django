from functools import lru_cache

from django.db.backends.base.base import NO_DB_ALIAS
from django.db.backends.postgresql.base import DatabaseWrapper as PsycopgDatabaseWrapper
from django.db.backends.postgresql.features import (
    DatabaseFeatures as PsycopgDatabaseFeatures,
)
from django.db.backends.postgresql.introspection import (
    DatabaseIntrospection as PsycopgDatabaseIntrospection,
)
from django.db.backends.postgresql.operations import (
    DatabaseOperations as PsycopgDatabaseOperations,
)
from django.db.backends.postgresql.psycopg_any import is_psycopg3

from .adapter import GEOSGeometry, PostGISAdapter
from .features import DatabaseFeatures
from .introspection import PostGISIntrospection
from .operations import PostGISOperations
from .schema import PostGISSchemaEditor

if is_psycopg3:
    from psycopg.adapt import Dumper
    from psycopg.pq import Format
    from psycopg.types import TypeInfo
    from psycopg.types.string import TextBinaryLoader, TextLoader

    class GeometryType:
        pass

    class GeographyType:
        pass

    class RasterType:
        pass

    class BaseTextDumper(Dumper):
        def dump(self, obj):
            # Return bytes as hex for text formatting
            return obj.ewkb.hex().encode()

    class BaseBinaryDumper(Dumper):
        format = Format.BINARY

        def dump(self, obj):
            return obj.ewkb

    @lru_cache
    def postgis_adapters(geo_oid, geog_oid, raster_oid):
        class BaseDumper(Dumper):
            def __init_subclass__(cls, base_dumper):
                super().__init_subclass__()

                cls.GeometryDumper = type(
                    "GeometryDumper", (base_dumper,), {"oid": geo_oid}
                )
                cls.GeographyDumper = type(
                    "GeographyDumper", (base_dumper,), {"oid": geog_oid}
                )
                cls.RasterDumper = type(
                    "RasterDumper", (BaseTextDumper,), {"oid": raster_oid}
                )

            def get_key(self, obj, format):
                if obj.is_geometry:
                    return GeographyType if obj.geography else GeometryType
                else:
                    return RasterType

            def upgrade(self, obj, format):
                if obj.is_geometry:
                    if obj.geography:
                        return self.GeographyDumper(GeographyType)
                    else:
                        return self.GeometryDumper(GeometryType)
                else:
                    return self.RasterDumper(RasterType)

            def dump(self, obj):
                raise NotImplementedError

        class PostGISTextDumper(BaseDumper, base_dumper=BaseTextDumper):
            pass

        class PostGISBinaryDumper(BaseDumper, base_dumper=BaseBinaryDumper):
            format = Format.BINARY

        return PostGISTextDumper, PostGISBinaryDumper

else:
    import psycopg2


# geometry array types caster for psycopg2
def geometry_array_caster(value, cursor):
    if value is None:
        return value
    text = value.strip("{}")
    if text == "":
        return []
    return [None if item == "NULL" else GEOSGeometry(item) for item in text.split(":")]


class DatabaseWrapper(PsycopgDatabaseWrapper):
    SchemaEditorClass = PostGISSchemaEditor
    features_class = DatabaseFeatures
    ops_class = PostGISOperations
    introspection_class = PostGISIntrospection

    _type_infos = {
        "geometry": {},
        "geography": {},
        "raster": {},
    }

    def __init__(self, *args, **kwargs):
        if kwargs.get("alias", "") == NO_DB_ALIAS:
            # Don't initialize PostGIS-specific stuff for non-db connections.
            self.features_class = PsycopgDatabaseFeatures
            self.ops_class = PsycopgDatabaseOperations
            self.introspection_class = PsycopgDatabaseIntrospection

        super().__init__(*args, **kwargs)

    def prepare_database(self):
        super().prepare_database()
        # Check that postgis extension is installed.
        with self.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = %s", ["postgis"])
            if bool(cursor.fetchone()):
                return
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            if is_psycopg3:
                # Ensure adapters are registers if PostGIS is used within this
                # connection.
                self.register_geometry_adapters(self.connection, True)
            else:
                # register caster for psycopg2
                self.register_geometry_array_casters(self.connection)

    def get_new_connection(self, conn_params):
        connection = super().get_new_connection(conn_params)
        if is_psycopg3:
            self.register_geometry_adapters(connection)
        else:
            self.register_geometry_array_casters(connection)
        return connection

    if is_psycopg3:

        def _register_type(self, pg_connection, typename):
            registry = self._type_infos[typename]
            try:
                info = registry[self.alias]
            except KeyError:
                info = TypeInfo.fetch(pg_connection, typename)
                registry[self.alias] = info

            if info:  # Can be None if the type does not exist (yet).
                info.register(pg_connection)
                pg_connection.adapters.register_loader(info.oid, TextLoader)
                pg_connection.adapters.register_loader(info.oid, TextBinaryLoader)

            return info.oid if info else None

        def register_geometry_adapters(self, pg_connection, clear_caches=False):
            if clear_caches:
                for typename in self._type_infos:
                    self._type_infos[typename].pop(self.alias, None)

            geo_oid = self._register_type(pg_connection, "geometry")
            geog_oid = self._register_type(pg_connection, "geography")
            raster_oid = self._register_type(pg_connection, "raster")

            PostGISTextDumper, PostGISBinaryDumper = postgis_adapters(
                geo_oid, geog_oid, raster_oid
            )
            pg_connection.adapters.register_dumper(PostGISAdapter, PostGISTextDumper)
            pg_connection.adapters.register_dumper(PostGISAdapter, PostGISBinaryDumper)

    # register geometry array type caster for psycopg2
    def register_geometry_array_casters(self, connection):
        """
        Register psycopg2 type casters for geometry[] and geography[] values.

        The array OIDs are looked up dynamically from pg_type because they may
        vary between databases. If the corresponding PostgreSQL types aren't
        available, no caster is registered.

        Custom casters are created with new_type() so that the PostgreSQL array
        value is passed to geometry_array_caster for explicit parsing.
        """

        old_autocommit = connection.autocommit
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT typname, typarray
                    FROM pg_type
                    WHERE typname IN (%s, %s)
                    """,
                    ("geometry", "geography"),
                )
                rows = dict(cursor.fetchall())
        finally:
            connection.autocommit = old_autocommit
        for typname, array_oid in rows.items():
            if not array_oid:
                continue
            caster = psycopg2.extensions.new_type(
                (array_oid,), f"{typname.upper()}[]", geometry_array_caster
            )
            psycopg2.extensions.register_type(caster)
