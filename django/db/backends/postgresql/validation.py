from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    def check_field_type(self, field, field_type):
        """PostgreSQL has limits on NUMERIC precision."""
        errors = []
    

        if field_type.startswith("numeric") and hasattr(field, 'max_digits') and hasattr(field, 'decimal_places'):
            if field.max_digits > 131072:
                errors.append(
                    checks.Warning(
                        "%s does not support DecimalField with max_digits > 131072." 
                        % self.connection.display_name,
                        obj=field,
                        id="postgresql.W001",
                    )
                )
            
            if field.decimal_places > 16383:
                errors.append(
                    checks.Warning(
                        "%s does not support DecimalField with decimal_places > 16383." 
                        % self.connection.display_name,
                        obj=field,
                        id="postgresql.W002",
                    )
                )
        
        return errors
    
