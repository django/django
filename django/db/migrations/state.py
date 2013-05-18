from django.db import models
from django.db.models.loading import BaseAppCache


class ProjectState(object):
    """
    Represents the entire project's overall state.
    This is the item that is passed around - we do it here rather than at the
    app level so that cross-app FKs/etc. resolve properly.
    """

    def __init__(self, models=None):
        self.models = models or {}
        self.app_cache = None

    def clone(self):
        "Returns an exact copy of this ProjectState"
        ps = ProjectState(
            models = dict((k, v.copy()) for k, v in self.models.items())
        )
        for model in ps.models.values():
            model.project_state = ps
        return ps

    def render(self):
        "Turns the project state into actual models in a new AppCache"
        if self.app_cache is None:
            self.app_cache = BaseAppCache()
            for model in self.model.values:
                model.render(self.app_cache)
        return self.app_cache

    @classmethod
    def from_app_cache(cls, app_cache):
        "Takes in an AppCache and returns a ProjectState matching it"
        for model in app_cache.get_models():
            print model


class ModelState(object):
    """
    Represents a Django Model. We don't use the actual Model class
    as it's not designed to have its options changed - instead, we
    mutate this one and then render it into a Model as required.
    """

    def __init__(self, project_state, app_label, name, fields=None, options=None, bases=None):
        self.project_state = project_state
        self.app_label = app_label
        self.name = name
        self.fields = fields or []
        self.options = options or {}
        self.bases = bases or None

    def clone(self):
        "Returns an exact copy of this ModelState"
        return self.__class__(
            project_state = self.project_state,
            app_label = self.app_label,
            name = self.name,
            fields = self.fields,
            options = self.options,
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
        if self.bases:
            raise NotImplementedError("Custom bases not quite done yet!")
        else:
            bases = [models.Model]
        # Turn fields into a dict for the body, add other bits
        body = dict(self.fields)
        body['Meta'] = meta
        body['__module__'] = "__fake__"
        # Then, make a Model object
        return type(
            self.name,
            tuple(bases),
            body,
        )
