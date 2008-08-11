from django.db.backends import BaseDatabaseValidation

class DatabaseValidation(BaseDatabaseValidation):
    def validate_field(self, errors, opts, f):
        "Prior to MySQL 5.0.3, character fields could not exceed 255 characters"
        from django.db import models
        from django.db import connection
        db_version = connection.get_server_version()
        if db_version < (5, 0, 3) and isinstance(f, (models.CharField, models.CommaSeparatedIntegerField, models.SlugField)) and f.max_length > 255:
            errors.add(opts,
                '"%s": %s cannot have a "max_length" greater than 255 when you are using a version of MySQL prior to 5.0.3 (you are using %s).' % 
                (f.name, f.__class__.__name__, '.'.join([str(n) for n in db_version[:3]])))
    