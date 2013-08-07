from django.db.backends import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    def validate_field(self, errors, opts, f):
        """
        MySQL has the following field length restriction:
        No character (varchar) fields can have a length exceeding 255
        characters if they have a unique index on them.
        """
        from django.db import models
        varchar_fields = (models.CharField, models.CommaSeparatedIntegerField,
                models.SlugField)
        if (isinstance(f, varchar_fields) and f.unique
                and (f.max_length is None or int(f.max_length) > 255)):
            msg = '"%(name)s": %(cls)s cannot have a "max_length" greater than 255 when using "unique=True".'
            errors.add(opts, msg % {'name': f.name, 'cls': f.__class__.__name__})
