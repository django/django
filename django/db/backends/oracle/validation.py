from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    def check_field_type(self, field, field_type):
        """
        Oracle doesn't support a database index on some data types.
        Oracle has limits on NUMBER precision and scale.
        """
        errors = []
        if field.db_index and field_type.lower() in self.connection._limited_data_types:
            errors.append(
                checks.Warning(
                    "Oracle does not support a database index on %s columns."
                    % field_type,
                    hint=(
                        "An index won't be created. Silence this warning if "
                        "you don't care about it."
                    ),
                    obj=field,
                    id="fields.W162",
                )
            )

        if field_type.startswith("number") and hasattr(field, 'max_digits') and hasattr(field, 'decimal_places'):
            if field.max_digits > 38:
                errors.append(
                    checks.Warning(
                        "%s does not support DecimalField with max_digits > 38." 
                        % self.connection.display_name,
                        obj=field,
                        id="oracle.W001",
                    )
                )
            
            if field.decimal_places > 127:
                errors.append(
                    checks.Warning(
                        "%s does not support DecimalField with decimal_places > 127." 
                        % self.connection.display_name,
                        obj=field,
                        id="oracle.W002",
                    )
                )
            

        return errors
