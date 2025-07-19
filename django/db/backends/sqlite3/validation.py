from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    def check_field_type(self, field, field_type):
        """SQLite has limitations on decimal precision and storage."""
        errors = []

        if (
            field_type.startswith("numeric")
            and hasattr(field, "max_digits")
            and hasattr(field, "decimal_places")
        ):
            if field.max_digits > 15 and field.decimal_places < 15:
                errors.append(
                    checks.Warning(
                        "%s stores only 15 significant digits for decimal values. "
                        "Values with max_digits > 15 may lose precision "
                        "and be stored as floating-point numbers."
                        % self.connection.display_name,
                        obj=field,
                        id="sqlite3.W001",
                    )
                )

            if field.max_digits > 15 and field.decimal_places > 15:
                errors.append(
                    checks.Warning(
                        "%s stores only 15 significant digits for decimal values. "
                        "Values with decimal_places > 15 may lose precision "
                        "and be stored as floating-point numbers."
                        % self.connection.display_name,
                        obj=field,
                        id="sqlite3.W002",
                    )
                )

        return errors
