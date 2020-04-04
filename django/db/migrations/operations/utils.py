from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT


def is_referenced_by_foreign_key(state, model_name_lower, field, field_name):
    for state_app_label, state_model in state.models:
        for _, f in state.models[state_app_label, state_model].fields:
            if (f.related_model and
                    '%s.%s' % (state_app_label, model_name_lower) == f.related_model.lower() and
                    hasattr(f, 'to_fields')):
                if (f.to_fields[0] is None and field.primary_key) or field_name in f.to_fields:
                    return True
    return False


def resolve_relation(model, app_label=None, model_name=None):
    """
    Turn a model class or model reference string and return a model tuple.

    app_label and model_name are used to resolve the scope of recursive and
    unscoped model relationship.
    """
    if isinstance(model, str):
        if model == RECURSIVE_RELATIONSHIP_CONSTANT:
            if app_label is None or model_name is None:
                raise TypeError(
                    'app_label and model_name must be provided to resolve '
                    'recursive relationships.'
                )
            return app_label, model_name
        if '.' in model:
            return tuple(model.lower().split('.', 1))
        if app_label is None:
            raise TypeError(
                'app_label must be provided to resolve unscoped model '
                'relationships.'
            )
        return app_label, model.lower()
    return model._meta.app_label, model._meta.model_name


def field_references_model(model_tuple, field, reference_model_tuple):
    """Return whether or not field references reference_model_tuple."""
    remote_field = field.remote_field
    if remote_field:
        if resolve_relation(remote_field.model, *model_tuple) == reference_model_tuple:
            return True
        through = getattr(remote_field, 'through', None)
        if through and resolve_relation(through, *model_tuple) == reference_model_tuple:
            return True
    return False
