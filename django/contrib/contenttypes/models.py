from __future__ import unicode_literals

import warnings

from django.apps import apps
from django.db import models
from django.db.utils import IntegrityError, OperationalError, ProgrammingError
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class ContentTypeManager(models.Manager):
    use_in_migrations = True

    # Cache to avoid re-looking up ContentType objects all over the place.
    # This cache is shared by all the get_for_* methods.
    _cache = {}

    def get_by_natural_key(self, app_label, model):
        try:
            ct = self.__class__._cache[self.db][(app_label, model)]
        except KeyError:
            ct = self.get(app_label=app_label, model=model)
            self._add_to_cache(self.db, ct)
        return ct

    def _get_opts(self, model, for_concrete_model):
        if for_concrete_model:
            model = model._meta.concrete_model
        elif model._deferred:
            model = model._meta.proxy_for_model
        return model._meta

    def _get_from_cache(self, opts):
        key = (opts.app_label, opts.model_name)
        return self.__class__._cache[self.db][key]

    def create(self, **kwargs):
        if 'name' in kwargs:
            del kwargs['name']
            warnings.warn(
                "ContentType.name field doesn't exist any longer. Please remove it from your code.",
                RemovedInDjango20Warning, stacklevel=2)
        return super(ContentTypeManager, self).create(**kwargs)

    def get_for_model(self, model, for_concrete_model=True):
        """
        Returns the ContentType object for a given model, creating the
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
            try:
                # We start with get() and not get_or_create() in order to use
                # the db_for_read (see #20401).
                ct = self.get(app_label=opts.app_label, model=opts.model_name)
            except self.model.DoesNotExist:
                # Not found in the database; we proceed to create it.  This time we
                # use get_or_create to take care of any race conditions.
                ct, created = self.get_or_create(
                    app_label=opts.app_label,
                    model=opts.model_name,
                )
        except (OperationalError, ProgrammingError, IntegrityError):
            # It's possible to migrate a single app before contenttypes,
            # as it's not a required initial dependency (it's contrib!)
            # Have a nice error for this.
            raise RuntimeError(
                "Error creating new content types. Please make sure contenttypes "
                "is migrated before trying to migrate apps individually."
            )
        self._add_to_cache(self.db, ct)
        return ct

    def get_for_models(self, *models, **kwargs):
        """
        Given *models, returns a dictionary mapping {model: content_type}.
        """
        for_concrete_models = kwargs.pop('for_concrete_models', True)
        # Final results
        results = {}
        # models that aren't already in the cache
        needed_app_labels = set()
        needed_models = set()
        needed_opts = set()
        for model in models:
            opts = self._get_opts(model, for_concrete_models)
            try:
                ct = self._get_from_cache(opts)
            except KeyError:
                needed_app_labels.add(opts.app_label)
                needed_models.add(opts.model_name)
                needed_opts.add(opts)
            else:
                results[model] = ct
        if needed_opts:
            cts = self.filter(
                app_label__in=needed_app_labels,
                model__in=needed_models
            )
            for ct in cts:
                model = ct.model_class()
                if model._meta in needed_opts:
                    results[model] = ct
                    needed_opts.remove(model._meta)
                self._add_to_cache(self.db, ct)
        for opts in needed_opts:
            # These weren't in the cache, or the DB, create them.
            ct = self.create(
                app_label=opts.app_label,
                model=opts.model_name,
            )
            self._add_to_cache(self.db, ct)
            results[ct.model_class()] = ct
        return results

    def get_for_id(self, id):
        """
        Lookup a ContentType by ID. Uses the same shared cache as get_for_model
        (though ContentTypes are obviously not created on-the-fly by get_by_id).
        """
        try:
            ct = self.__class__._cache[self.db][id]
        except KeyError:
            # This could raise a DoesNotExist; that's correct behavior and will
            # make sure that only correct ctypes get stored in the cache dict.
            ct = self.get(pk=id)
            self._add_to_cache(self.db, ct)
        return ct

    def clear_cache(self):
        """
        Clear out the content-type cache. This needs to happen during database
        flushes to prevent caching of "stale" content type IDs (see
        django.contrib.contenttypes.management.update_contenttypes for where
        this gets called).
        """
        self.__class__._cache.clear()

    def _add_to_cache(self, using, ct):
        """Insert a ContentType into the cache."""
        # Note it's possible for ContentType objects to be stale; model_class() will return None.
        # Hence, there is no reliance on model._meta.app_label here, just using the model fields instead.
        key = (ct.app_label, ct.model)
        self.__class__._cache.setdefault(using, {})[key] = ct
        self.__class__._cache.setdefault(using, {})[ct.id] = ct


@python_2_unicode_compatible
class ContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(_('python model class name'), max_length=100)
    objects = ContentTypeManager()

    class Meta:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)

    def __str__(self):
        return self.name

    @property
    def name(self):
        model = self.model_class()
        if not model:
            return self.model
        return force_text(model._meta.verbose_name)

    def model_class(self):
        "Returns the Python model class for this type of content."
        try:
            return apps.get_model(self.app_label, self.model)
        except LookupError:
            return None

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.model_class()._base_manager.using(self._state.db).get(**kwargs)

    def get_all_objects_for_this_type(self, **kwargs):
        """
        Returns all objects of this type for the keyword arguments given.
        """
        return self.model_class()._base_manager.using(self._state.db).filter(**kwargs)

    def natural_key(self):
        return (self.app_label, self.model)
