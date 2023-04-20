from collections import defaultdict

from django.apps import apps
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ContentTypeManager(models.Manager):
    use_in_migrations = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache shared by all the get_for_* methods to speed up
        # ContentType retrieval.
        self._cache = {}

    def get_by_natural_key(self, app_label, model):
        try:
            ct = self._cache[self.db][(app_label, model)]
        except KeyError:
            ct = self.get(app_label=app_label, model=model)
            self._add_to_cache(self.db, ct)
        return ct

    def _get_opts(self, model, for_concrete_model):
        if for_concrete_model:
            model = model._meta.concrete_model
        return model._meta

    def _get_from_cache(self, opts):
        key = (opts.app_label, opts.model_name)
        return self._cache[self.db][key]

    def get_for_model(self, model, for_concrete_model=True):
        """
        Return the ContentType object for a given model, creating the
        ContentType if necessary. Lookups are cached so that subsequent lookups
        for the same model don't hit the database.
        """
        opts = self._get_opts(model, for_concrete_model)
        try:
            return self._get_from_cache(opts)
        except KeyError:
            pass

        # The ContentType entry was not found in the cache, therefore we
        # proceed to load or create it.
        try:
            # Start with get() and not get_or_create() in order to use
            # the db_for_read (see #20401).
            ct = self.get(app_label=opts.app_label, model=opts.model_name)
        except self.model.DoesNotExist:
            # Not found in the database; we proceed to create it. This time
            # use get_or_create to take care of any race conditions.
            ct, created = self.get_or_create(
                app_label=opts.app_label,
                model=opts.model_name,
            )
        self._add_to_cache(self.db, ct)
        return ct

    def get_for_models(self, *models, for_concrete_models=True):
        """
        Given *models, return a dictionary mapping {model: content_type}.
        """
        results = {}
        # Models that aren't already in the cache grouped by app labels.
        needed_models = defaultdict(set)
        # Mapping of opts to the list of models requiring it.
        needed_opts = defaultdict(list)
        for model in models:
            opts = self._get_opts(model, for_concrete_models)
            try:
                ct = self._get_from_cache(opts)
            except KeyError:
                needed_models[opts.app_label].add(opts.model_name)
                needed_opts[opts].append(model)
            else:
                results[model] = ct
        if needed_opts:
            # Lookup required content types from the DB.
            condition = Q(
                *(
                    Q(("app_label", app_label), ("model__in", models))
                    for app_label, models in needed_models.items()
                ),
                _connector=Q.OR,
            )
            cts = self.filter(condition)
            for ct in cts:
                opts_models = needed_opts.pop(
                    ct._meta.apps.get_model(ct.app_label, ct.model)._meta, []
                )
                for model in opts_models:
                    results[model] = ct
                self._add_to_cache(self.db, ct)
        # Create content types that weren't in the cache or DB.
        for opts, opts_models in needed_opts.items():
            ct = self.create(
                app_label=opts.app_label,
                model=opts.model_name,
            )
            self._add_to_cache(self.db, ct)
            for model in opts_models:
                results[model] = ct
        return results

    def get_for_id(self, id):
        """
        Lookup a ContentType by ID. Use the same shared cache as get_for_model
        (though ContentTypes are not created on-the-fly by get_by_id).
        """
        try:
            ct = self._cache[self.db][id]
        except KeyError:
            # This could raise a DoesNotExist; that's correct behavior and will
            # make sure that only correct ctypes get stored in the cache dict.
            ct = self.get(pk=id)
            self._add_to_cache(self.db, ct)
        return ct

    def clear_cache(self):
        """
        Clear out the content-type cache.
        """
        self._cache.clear()

    def _add_to_cache(self, using, ct):
        """Insert a ContentType into the cache."""
        # Note it's possible for ContentType objects to be stale; model_class()
        # will return None. Hence, there is no reliance on
        # model._meta.app_label here, just using the model fields instead.
        key = (ct.app_label, ct.model)
        self._cache.setdefault(using, {})[key] = ct
        self._cache.setdefault(using, {})[ct.id] = ct


class ContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(_("python model class name"), max_length=100)
    objects = ContentTypeManager()

    class Meta:
        verbose_name = _("content type")
        verbose_name_plural = _("content types")
        db_table = "django_content_type"
        unique_together = [["app_label", "model"]]

    def __str__(self):
        return self.app_labeled_name

    @property
    def name(self):
        model = self.model_class()
        if not model:
            return self.model
        return str(model._meta.verbose_name)

    @property
    def app_labeled_name(self):
        model = self.model_class()
        if not model:
            return self.model
        return "%s | %s" % (
            model._meta.app_config.verbose_name,
            model._meta.verbose_name,
        )

    def model_class(self):
        """Return the model class for this type of content."""
        try:
            return apps.get_model(self.app_label, self.model)
        except LookupError:
            return None

    def get_object_for_this_type(self, **kwargs):
        """
        Return an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.model_class()._base_manager.using(self._state.db).get(**kwargs)

    def get_all_objects_for_this_type(self, **kwargs):
        """
        Return all objects of this type for the keyword arguments given.
        """
        return self.model_class()._base_manager.using(self._state.db).filter(**kwargs)

    def natural_key(self):
        return (self.app_label, self.model)
