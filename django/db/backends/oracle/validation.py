from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    def check_field_type(self, field, field_type):
        """Oracle doesn't support a database index on some data types."""
        errors = []
        if field.db_index and field_type.lower() in self.connection._limited_data_types:
            errors.append(
                checks.Warning(
                    f"Oracle does not support a database index on {field_type} columns.",
                    hint=(
                        "An index won't be created. Silence this warning if "
                        "you don't care about it."
                    ),
                    obj=field,
                    id="fields.W162",
                )
            )
        return errors
