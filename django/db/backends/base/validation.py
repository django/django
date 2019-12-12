from django.core import checks


class BaseDatabaseValidation:
    """Encapsulate backend-specific validation."""
    def __init__(self, connection):
        self.connection = connection

    def check(self, **kwargs):
        return []

    def check_model(self, model, **kwargs):
        db_supports_all_required_features = all(
            getattr(self.connection.features, feature, False)
            for feature in model._meta.required_db_features
        )
        if not db_supports_all_required_features:
            return []
        return self._check_model(model, **kwargs)

    def _check_model(self, model, **kwargs):
        return [
            *self._check_fields(model, **kwargs),
            *self._check_constraints(model, **kwargs)
        ]

    def _check_fields(self, model, **kwargs):
        errors = []
        for field in model._meta.local_fields:
            errors.extend(self.check_field(field, **kwargs))
        for field in model._meta.local_many_to_many:
            errors.extend(self.check_field(field, from_model=model, **kwargs))
        return errors

    def check_field(self, field, **kwargs):
        field_type = field.db_type(self.connection)
        # Ignore non-concrete fields.
        if field_type is not None:
            return self.check_field_type(field, field_type)
        return []

    def check_field_type(self, field, field_type):
        return []

    def _check_constraints(self, model, **kwargs):
        errors = []
        for constraint in model._meta.constraints:
            if constraint.supported(self.connection):
                continue
            errors.append(
                checks.Warning(
                    '%s does not support %r.' % (self.connection.display_name, constraint),
                    hint=(
                        "A constraint won't be created. Silence this "
                        "warning if you don't care about it."
                    ),
                    obj=model,
                    id='models.W027',
                )
            )
        return errors
