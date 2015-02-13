from django.utils import six


def make_model_label(model):
    """
    Takes a model or a tuple of the form (app_label, model_name) and returns a
    corresponding "app_label.ModelName" string. If a string is passed in, it's
    assumed to be a valid model label already and returned unchanged.
    """
    if isinstance(model, six.string_types):
        return model
    if isinstance(model, tuple):
        return "%s.%s" % model
    return "%s.%s" % (model._meta.app_label, model._meta.object_name)


def make_model_tuple(model):
    """
    Takes a model or a string of the form "app_label.ModelName" and returns a
    corresponding (app_label, model_name) tuple. If a tuple is passed in, it's
    assumed to be a valid model tuple already and returned unchanged.
    """
    if isinstance(model, tuple):
        return model
    if isinstance(model, six.string_types):
        return tuple(model.split("."))
    return model._meta.app_label, model._meta.object_name
