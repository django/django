
from django.core.exceptions import ImproperlyConfigured

try:
    from django.db.backends.sqlite3.base import SQLiteCursorWrapper
    HAS_SQLITE = True
except ImproperlyConfigured as exc:
    HAS_SQLITE = False

if HAS_SQLITE:
    class LoggingCursor(SQLiteCursorWrapper):
        """
        A cursor that will log all statements in it's bucket
        """

        def __init__(self, *args, **kwargs):
            bucket = kwargs.pop('bucket')
            super(LoggingCursor, self).__init__(*args, **kwargs)
            self.bucket = bucket

        def execute(self, sql, *args, **kwargs):
            self.bucket.append(sql)
            super(LoggingCursor, self).execute(sql, *args, **kwargs)

    class LoggingCursorFactory(object):
        """
        Factory class, will create intances of the logging cursor with a
        shared bucket.
        """
        def __init__(self, bucket=None):
            super(LoggingCursorFactory, self).__init__()
            if bucket is None:
                bucket = list()
            self.bucket = bucket

        def create(self, *args, **kwargs):
            kwargs.setdefault('bucket', self.bucket)
            return LoggingCursor(*args, **kwargs)
