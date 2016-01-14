from django.utils import six


def make_model_tuple(model):
    """
    Takes a model or a string of the form "app_label.ModelName" and returns a
    corresponding ("app_label", "modelname") tuple. If a tuple is passed in,
    it's assumed to be a valid model tuple already and returned unchanged.
    """
    if isinstance(model, tuple):
        model_tuple = model
    elif isinstance(model, six.string_types):
        app_label, model_name = model.split(".")
        model_tuple = app_label, model_name.lower()
    else:
        model_tuple = model._meta.app_label, model._meta.model_name
    assert len(model_tuple) == 2, "Invalid model representation: %s" % model
    return model_tuple
