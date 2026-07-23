import warnings

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper

from .features import DatabaseFeatures
from .introspection import MySQLIntrospection
from .operations import MySQLOperations as BaseMySQLOperations
from .schema import MySQLGISSchemaEditor


class MySQLOperations(BaseMySQLOperations):
    """Custom operations that handle information_schema specially."""

    def quote_name(self, name):
        if "information_schema" in name:
            return name
        return super().quote_name(name)


class DatabaseWrapper(MySQLDatabaseWrapper):
    SchemaEditorClass = MySQLGISSchemaEditor
    features_class = DatabaseFeatures
    introspection_class = MySQLIntrospection
    ops_class = MySQLOperations

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mysql8_cache = None
        self._geometry_binary_set = False

    # -------------------------------
    # Database preparation
    # -------------------------------
    def prepare_database(self):
        super().prepare_database()

        # ✅ Warm up version cache safely
        self.is_mysql8()

        if self._mysql8_cache:
            self._verify_spatial_support()

    def _verify_spatial_support(self):
        try:
            with self.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.st_spatial_reference_systems
                    LIMIT 1
                    """)
                cursor.fetchone()
        except Exception as e:
            warnings.warn(
                ("MySQL 8.0 spatial reference systems may not " f"be accessible: {e}"),
                RuntimeWarning,
                stacklevel=2,
            )

    # -------------------------------
    # Version detection (SAFE)
    # -------------------------------
    def is_mysql8(self):
        """
        Detect MySQL 8.0+ without triggering recursion.
        """
        if self._mysql8_cache is None:
            try:
                # ✅ Use raw cursor WITHOUT calling is_mysql8 again
                cursor = super().create_cursor()
                try:
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()[0]
                finally:
                    cursor.close()

                self._mysql8_cache = (
                    version.startswith("8.") and "MariaDB" not in version
                )
            except Exception:
                self._mysql8_cache = False

        return self._mysql8_cache

    # -------------------------------
    # Geometry handling
    # -------------------------------
    def get_geometry_converter(self, expression):
        if self._mysql8_cache:
            return self.ops.get_geometry_converter(expression)
        return super().get_geometry_converter(expression)

    # -------------------------------
    # Cursor handling (NO recursion)
    # -------------------------------
    def create_cursor(self, name=None):
        cursor = super().create_cursor(name)

        # ✅ Only use cached value (NO function calls here)
        if self._mysql8_cache and not self._geometry_binary_set:
            try:
                cursor.execute("SET @_geometry_binary_format = 'wkb'")
                self._geometry_binary_set = True
            except Exception as e:
                warnings.warn(
                    f"Could not set geometry binary format: {e}",
                    RuntimeWarning,
                )

        return cursor
