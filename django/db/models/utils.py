from django.core.exceptions import FieldDoesNotExist
from django.db import models
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


def iter_lookup(opts, lookup_path, include_lookup=False):
    """
    Iterator over model Fields (by default) including Lookup as the last
    element.
    """
    if isinstance(opts, models.Model):
        opts = opts._meta

    lookup_fields = lookup_path.split(LOOKUP_SEP)
    # Go through the fields (following all relations) and look for an m2m
    prev_field = None
    for field_name in lookup_fields:
        if field_name == 'pk':
            field_name = opts.pk.name
        try:
            field = opts.get_field(field_name)
        except FieldDoesNotExist:
            # Ignore valid query lookups.
            lookup = prev_field and prev_field.get_lookup(field_name)
            if include_lookup and lookup:
                yield lookup
            return  # just exit if this field does not exist, next one will not exist either
        else:
            yield field
            prev_field = field
            if hasattr(field, 'get_path_info'):
                # This field is a relation, update opts to follow the relation
                path_info = field.get_path_info()
                opts = path_info[-1].to_opts


def fields_need_distinct(fields):
    """
    Return True if 'distinct()' should be used to query given fields.
    """
    for field in fields:
        if hasattr(field, 'get_path_info'):
            path_info = field.get_path_info()
            if any(path.m2m for path in path_info):
                # This field is a m2m relation so we know we need to call distinct
                return True
    return False
