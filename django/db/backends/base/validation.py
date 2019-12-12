class BaseDatabaseValidation:
    """Encapsulate backend-specific validation."""
    def __init__(self, connection):
        self.connection = connection

    def check(self, **kwargs):
        return []

    def check_model(self, model, **kwargs):
        errors = []
        db_supports_all_required_features = all(
            getattr(self.connection.features, feature, False)
            for feature in model._meta.required_db_features
        )
        if not db_supports_all_required_features:
            return errors
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
