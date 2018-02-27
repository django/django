def is_referenced_by_foreign_key(state, model_name_lower, field, field_name):
    for state_app_label, state_model in state.models:
        for _, f in state.models[state_app_label, state_model].fields:
            if (f.related_model and
                    '%s.%s' % (state_app_label, model_name_lower) == f.related_model.lower() and
                    hasattr(f, 'to_fields')):
                if (f.to_fields[0] is None and field.primary_key) or field_name in f.to_fields:
                    return True
    return False
