from django.db import DEFAULT_DB_ALIAS


class TestRouter:
    """
    Vaguely behave like primary/replica, but the databases aren't assumed to
    propagate changes.
    """

    def db_for_read(self, model, instance=None, **hints):
        if instance:
            return instance._state.db or 'other'
        return 'other'

    def db_for_write(self, model, **hints):
        return DEFAULT_DB_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in ('default', 'other') and obj2._state.db in ('default', 'other')

    def allow_migrate(self, db, app_label, **hints):
        return True


class AuthRouter:
    """
    Control all database operations on models in the contrib.auth application.
    """

    def db_for_read(self, model, **hints):
        "Point all read operations on auth models to 'default'"
        if model._meta.app_label == 'auth':
            # We use default here to ensure we can tell the difference
            # between a read request and a write request for Auth objects
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on auth models to 'other'"
        if model._meta.app_label == 'auth':
            return 'other'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in Auth is involved"
        if obj1._meta.app_label == 'auth' or obj2._meta.app_label == 'auth':
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        "Make sure the auth app only appears on the 'other' db"
        if app_label == 'auth':
            return db == 'other'
        return None


class WriteRouter:
    # A router that only expresses an opinion on writes
    def db_for_write(self, model, **hints):
        return 'writer'
