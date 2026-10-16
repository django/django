from django.db.backends.base.features import BaseDatabaseFeatures


class DummyDatabaseFeatures(BaseDatabaseFeatures):
    supports_transactions = False
    uses_savepoints = False
    supports_same_table_select_as_update = True
