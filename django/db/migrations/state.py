from django.db import models
from django.db.models.loading import BaseAppCache
from django.db.models.options import DEFAULT_NAMES
from django.utils import six
from django.utils.module_loading import import_by_path


class InvalidBasesError(ValueError):
    pass


class ProjectState(object):
    """
    Represents the entire project's overall state.
    This is the item that is passed around - we do it here rather than at the
    app level so that cross-app FKs/etc. resolve properly.
    """

    def __init__(self, models=None):
        self.models = models or {}
        self.app_cache = None

    def add_model_state(self, model_state):
        self.models[(model_state.app_label, model_state.name.lower())] = model_state

    def clone(self):
        "Returns an exact copy of this ProjectState"
        return ProjectState(
            models = dict((k, v.clone()) for k, v in self.models.items())
        )

    def render(self):
        "Turns the project state into actual models in a new AppCache"
        if self.app_cache is None:
            self.app_cache = BaseAppCache()
            # We keep trying to render the models in a loop, ignoring invalid
            # base errors, until the size of the unrendered models doesn't
            # decrease by at least one, meaning there's a base dependency loop/
            # missing base.
            unrendered_models = list(self.models.values())
            while unrendered_models:
                new_unrendered_models = []
                for model in unrendered_models:
                    try:
                        model.render(self.app_cache)
                    except InvalidBasesError:
                        new_unrendered_models.append(model)
                if len(new_unrendered_models) == len(unrendered_models):
                    raise InvalidBasesError("Cannot resolve bases for %r" % new_unrendered_models)
                unrendered_models = new_unrendered_models
        return self.app_cache

    @classmethod
    def from_app_cache(cls, app_cache):
        "Takes in an AppCache and returns a ProjectState matching it"
        models = {}
        for model in app_cache.get_models():
            model_state = ModelState.from_model(model)
            models[(model_state.app_label, model_state.name.lower())] = model_state
        return cls(models)


class ModelState(object):
    """
    Represents a Django Model. We don't use the actual Model class
    as it's not designed to have its options changed - instead, we
    mutate this one and then render it into a Model as required.

    Note that while you are allowed to mutate .fields, you are not allowed
    to mutate the Field instances inside there themselves - you must instead
    assign new ones, as these are not detached during a clone.
    """

    def __init__(self, app_label, name, fields, options=None, bases=None):
        self.app_label = app_label
        self.name = name
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model, )
        # Sanity-check that fields is NOT a dict. It must be ordered.
        if isinstance(self.fields, dict):
            raise ValueError("ModelState.fields cannot be a dict - it must be a list of 2-tuples.")

    @classmethod
    def from_model(cls, model):
        """
        Feed me a model, get a ModelState representing it out.
        """
        # Deconstruct the fields
        fields = []
        for field in model._meta.local_fields:
            name, path, args, kwargs = field.deconstruct()
            field_class = import_by_path(path)
            fields.append((name, field_class(*args, **kwargs)))
        # Extract the options
        options = {}
        for name in DEFAULT_NAMES:
            # Ignore some special options
            if name in ["app_cache", "app_label"]:
                continue
            elif name in model._meta.original_attrs:
                if name == "unique_together":
                    options[name] = set(model._meta.original_attrs["unique_together"])
                else:
                    options[name] = model._meta.original_attrs[name]
        # Make our record
        bases = tuple(
            ("%s.%s" % (base._meta.app_label, base._meta.object_name.lower()) if hasattr(base, "_meta") else base)
            for base in model.__bases__
            if (not hasattr(base, "_meta") or not base._meta.abstract)
        )
        if not bases:
            bases = (models.Model, )
        return cls(
            model._meta.app_label,
            model._meta.object_name,
            fields,
            options,
            bases,
        )

    def clone(self):
        "Returns an exact copy of this ModelState"
        # We deep-clone the fields using deconstruction
        fields = []
        for name, field in self.fields:
            _, path, args, kwargs = field.deconstruct()
            field_class = import_by_path(path)
            fields.append((name, field_class(*args, **kwargs)))
        # Now make a copy
        return self.__class__(
            app_label = self.app_label,
            name = self.name,
            fields = fields,
            options = dict(self.options),
            bases = self.bases,
        )

    def render(self, app_cache):
        "Creates a Model object from our current state into the given app_cache"
        # First, make a Meta object
        meta_contents = {'app_label': self.app_label, "app_cache": app_cache}
        meta_contents.update(self.options)
        if "unique_together" in meta_contents:
            meta_contents["unique_together"] = list(meta_contents["unique_together"])
        meta = type("Meta", tuple(), meta_contents)
        # Then, work out our bases
        bases = tuple(
            (app_cache.get_model(*base.split(".", 1)) if isinstance(base, six.string_types) else base)
            for base in self.bases
        )
        if None in bases:
            raise InvalidBasesError("Cannot resolve one or more bases from %r" % self.bases)
        # Turn fields into a dict for the body, add other bits
        body = dict(self.fields)
        body['Meta'] = meta
        body['__module__'] = "__fake__"
        # Then, make a Model object
        return type(
            self.name,
            bases,
            body,
        )

    def get_field_by_name(self, name):
        for fname, field in self.fields:
            if fname == name:
                return field
        raise ValueError("No field called %s on model %s" % (name, self.name))
