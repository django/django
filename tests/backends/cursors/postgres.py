try:
    import psycopg2
    import psycopg2.extensions
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    pass

if HAS_PSYCOPG2:
    class LoggingCursor(psycopg2.extensions.cursor):
        def __init__(self, *args, **kwargs):
            bucket = kwargs.pop('bucket')
            super(LoggingCursor, self).__init__(*args, **kwargs)
            self.bucket = bucket

        def execute(self, sql, args=None):
            self.bucket.append(self.mogrify(sql, args))
            psycopg2.extensions.cursor.execute(self, sql, args)

    class LoggingCursorFactory(object):
        """docstring for LoggingCursorFactory."""
        def __init__(self, bucket=None):
            super(LoggingCursorFactory, self).__init__()
            if bucket is None:
                bucket = list()
            self.bucket = bucket

        def create(self, *args, **kwargs):
            kwargs.update({
                'bucket': self.bucket
            })
            return LoggingCursor(*args, **kwargs)
