from django.contrib.postgres.indexes import PostgresIndex


class DummyIndex(PostgresIndex):
    """A dummy index to demonstrate a custom suffix distinct from the indexing method"""

    suffix = "dummy"

    def create_sql(self, model, schema_editor, using="gin", **kwargs):
        return super().create_sql(model, schema_editor, using=using, **kwargs)

    def deconstruct(self):
        # for some reason all tests check path as well; this exists to fool
        # them into seeing this class as part of the builtin index classes
        _, args, kwargs = super().deconstruct()
        path = "django.contrib.postgres.indexes.%s" % self.__class__.__name__
        return path, args, kwargs
