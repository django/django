import warnings

from django.db.backends.mysql.base import DatabaseOperations
from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper

from .features import DatabaseFeatures
from .introspection import MySQLIntrospection
from .operations import MySQLOperations
from .schema import MySQLGISSchemaEditor


class MySQLDatabaseOperations(DatabaseOperations):
    """Custom operations that handle information_schema specially."""

    def quote_name(self, name):
        """
        Prevent quoting or prefixing for information_schema tables.
        """
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

        # Cache for MySQL 8.0 detection
        self._mysql8_cache = None
        self._geometry_binary_set = False  # For cursor optimization

        # Replace default ops with GIS-aware ops
        self.ops = MySQLOperations(self)
        # Override quote_name for information_schema tables
        self.ops.quote_name = self._quote_name_for_information_schema

    def _quote_name_for_information_schema(self, name):
        """
        Quote table names, handling information_schema specially.
        """
        if "information_schema" in name:
            return name
        return super(MySQLOperations, self.ops).quote_name(name)

    def prepare_database(self):
        """Prepare the database for GIS support."""
        super().prepare_database()
        if self.is_mysql8():
            self._verify_spatial_support()

    def _verify_spatial_support(self):
        """
        Verify that MySQL 8.0 spatial features are accessible.
        Warn if ST_SPATIAL_REFERENCE_SYSTEMS cannot be read.
        """
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
                f"MySQL 8.0 spatial reference systems may not be accessible: {e}",
                RuntimeWarning,
                stacklevel=2,
            )

    def is_mysql8(self):
        """Return True if using MySQL 8.0+ and not MariaDB."""
        if self._mysql8_cache is None:
            try:
                self._mysql8_cache = getattr(self, "mysql_version", (0, 0)) >= (
                    8,
                    0,
                ) and not getattr(self, "mysql_is_mariadb", False)
            except AttributeError:
                self._mysql8_cache = False
        return self._mysql8_cache

    def get_geometry_converter(self, expression):
        """
        Return a converter for geometry values.
        Uses enhanced MySQL 8.0 handling if available.
        """
        if self.is_mysql8():
            return self.ops.get_geometry_converter(expression)
        return super().get_geometry_converter(expression)

    def _set_autocommit(self, value):
        """
        Set the autocommit mode for the database connection.

        This override exists to handle any GIS-specific transaction
        requirements, though currently it just calls the parent method.
        """
        super()._set_autocommit(value)

    def create_cursor(self, name=None):
        cursor = super().create_cursor(name)

        # Cache the MySQL 8.0 check after first cursor creation
        if not hasattr(self, "_mysql8_cached"):
            try:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                self._mysql8_cached = "8." in version and "MariaDB" not in version
            except Exception:
                self._mysql8_cached = False

        if self._mysql8_cached and not self._geometry_binary_set:
            try:
                cursor.execute("SET @_geometry_binary_format = 'wkb'")
                self._geometry_binary_set = True
            except Exception:
                pass

        return cursor
