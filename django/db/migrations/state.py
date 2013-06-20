from django.db import models
from django.db.models.loading import BaseAppCache
from django.db.models.options import DEFAULT_NAMES
from django.utils.module_loading import import_by_path


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
            for model in self.models.values():
                model.render(self.app_cache)
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
            if name in model._meta.original_attrs:
                options[name] = model._meta.original_attrs[name]
        # Make our record
        return cls(
            model._meta.app_label,
            model._meta.object_name,
            fields,
            options,
            model.__bases__,
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
        meta = type("Meta", tuple(), meta_contents)
        # Then, work out our bases
        # TODO: Use the actual bases
        # Turn fields into a dict for the body, add other bits
        body = dict(self.fields)
        body['Meta'] = meta
        body['__module__'] = "__fake__"
        # Then, make a Model object
        return type(
            self.name,
            tuple(self.bases),
            body,
        )
