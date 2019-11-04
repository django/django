from collections import namedtuple

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


class ModelTuple(namedtuple('ModelTupleBase', ('app_label', 'model_name'))):
    @classmethod
    def from_model(cls, model, app_label=None, model_name=None):
        """
        Take a model class or a 'app_label.ModelName' string and return a
        ModelTuple('app_label', 'modelname'). The optional app_label and
        model_name arguments are the defaults if "self" or "ModelName" are
        passed.
        """
        if isinstance(model, str):
            if model == RECURSIVE_RELATIONSHIP_CONSTANT:
                return cls(app_label, model_name)
            if '.' in model:
                return cls(*model.lower().split('.', 1))
            return cls(app_label, model.lower())
        return cls(model._meta.app_label, model._meta.model_name)

    def __eq__(self, other):
        if isinstance(other, ModelTuple):
            # Consider ModelTuple equal if their model_name is equal and either
            # one of them is missing an app_label.
            return self.model_name == other.model_name and (
                self.app_label is None or other.app_label is None or self.app_label == other.app_label
            )
        return super().__eq__(other)


def field_references_model(field, model_tuple):
    """Return whether or not field references model_tuple."""
    remote_field = field.remote_field
    if remote_field:
        if ModelTuple.from_model(remote_field.model) == model_tuple:
            return True
        through = getattr(remote_field, 'through', None)
        if through and ModelTuple.from_model(through) == model_tuple:
            return True
    return False
