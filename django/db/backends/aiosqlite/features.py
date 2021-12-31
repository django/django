import operator

from asgiref.sync import async_to_sync

from django.db import transaction
from django.db.backends.sqlite3.features import (
    DatabaseFeatures as SQLiteDatabaseFeatures,
)
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from .base import Database


class DatabaseFeatures(SQLiteDatabaseFeatures):
    @cached_property
    def django_test_skips(self):
        return self._django_test_skips(Database.sqlite_version_info)

    @cached_property
    def supports_atomic_references_rename(self):
        return Database.sqlite_version_info >= (3, 26, 0)

    async def _supports_json_field(self):
        with await self.connection.cursor() as cursor:
            try:
                async with transaction.aatomic(self.connection.alias):
                    await cursor.execute('SELECT JSON(\'{"a": "b"}\')')
            except OperationalError:
                return False
        return True

    @cached_property
    def supports_json_field(self):
        return async_to_sync(self._supports_json_field)()

    can_introspect_json_field = property(operator.attrgetter('supports_json_field'))
    has_json_object_function = property(operator.attrgetter('supports_json_field'))

    @cached_property
    def can_return_columns_from_insert(self):
        return Database.sqlite_version_info >= (3, 35)

    can_return_rows_from_bulk_insert = property(operator.attrgetter('can_return_columns_from_insert'))
