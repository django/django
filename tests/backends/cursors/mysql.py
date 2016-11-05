
try:
    from MySQLdb.cursors import Cursor
    HAS_MYSQL = True
except ImportError as exc:
    HAS_MYSQL = False

if HAS_MYSQL:
    class LoggingCursor(Cursor):
        """
        A cursor that will log all statements in it's bucket
        """
        def __init__(self, *args, **kwargs):
            bucket = kwargs.pop('bucket')
            super(LoggingCursor, self).__init__(*args, **kwargs)
            self.bucket = bucket

        def execute(self, query, args=None):
            self.bucket.append(query)
            super(LoggingCursor, self).execute(query, args)

    class LoggingCursorFactory(object):
        def __init__(self, bucket=None):
            super(LoggingCursorFactory, self).__init__()
            if bucket is None:
                bucket = list()
            self.bucket = bucket

        def create(self, *args, **kwargs):
            kwargs.setdefault('bucket', self.bucket)
            return LoggingCursor(*args, **kwargs)
