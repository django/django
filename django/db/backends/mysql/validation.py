from django.db.backends import BaseDatabaseValidation

class DatabaseValidation(BaseDatabaseValidation):
    def validate_field(self, errors, opts, f):
        """
        There are some field length restrictions for MySQL:

        - Prior to version 5.0.3, character fields could not exceed 255
          characters in length.
        - No character (varchar) fields can have a length exceeding 255
          characters if they have a unique index on them.
        """
        from django.db import models
        from django.db import connection
        db_version = connection.get_server_version()
        varchar_fields = (models.CharField, models.CommaSeparatedIntegerField,
                models.SlugField)
        if isinstance(f, varchar_fields) and f.max_length > 255:
            if db_version < (5, 0, 3):
                msg = '"%(name)s": %(cls)s cannot have a "max_length" greater than 255 when you are using a version of MySQL prior to 5.0.3 (you are using %(version)s).'
            elif f.unique == True:
                msg = '"%(name)s": %(cls)s cannot have a "max_length" greater than 255 when using "unique=True".'
            else:
                msg = None

            if msg:
                errors.add(opts, msg % {'name': f.name, 'cls': f.__class__.__name__, 'version': '.'.join([str(n) for n in db_version[:3]])})

