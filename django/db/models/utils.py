from django.db.models.constants import LOOKUP_SEP


def make_model_tuple(model):
    """
    Take a model or a string of the form "app_label.ModelName" and return a
    corresponding ("app_label", "modelname") tuple. If a tuple is passed in,
    assume it's a valid model tuple already and return it unchanged.
    """
    try:
        if isinstance(model, tuple):
            model_tuple = model
        elif isinstance(model, str):
            app_label, model_name = model.split(".")
            model_tuple = app_label, model_name.lower()
        else:
            model_tuple = model._meta.app_label, model._meta.model_name
        assert len(model_tuple) == 2
        return model_tuple
    except (ValueError, AssertionError):
        raise ValueError(
            "Invalid model reference '%s'. String model references "
            "must be of the form 'app_label.ModelName'." % model
        )


def get_field_from_path(model, path):
    pieces = path.split(LOOKUP_SEP)
    fields = []
    for piece in pieces:
        parent = model
        if (fields and fields[-1].is_relation and
                fields[-1].remote_field.model != model):
            parent = fields[-1].remote_field.model
        fields.append(parent._meta.get_field(piece))

    return fields[-1]
