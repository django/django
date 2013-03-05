from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text, force_text
from django.utils.encoding import python_2_unicode_compatible

class ContentTypeManager(models.Manager):

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

    def get_for_model(self, model, for_concrete_model=True):
        """
        Returns the ContentType object for a given model, creating the
        ContentType if necessary. Lookups are cached so that subsequent lookups
        for the same model don't hit the database.
        """
        opts = self._get_opts(model, for_concrete_model)
        try:
            ct = self._get_from_cache(opts)
        except KeyError:
            # Load or create the ContentType entry. The smart_text() is
            # needed around opts.verbose_name_raw because name_raw might be a
            # django.utils.functional.__proxy__ object.
            ct, created = self.get_or_create(
                app_label = opts.app_label,
                model = opts.model_name,
                defaults = {'name': smart_text(opts.verbose_name_raw)},
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
                name=smart_text(opts.verbose_name_raw),
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
        model = ct.model_class()
        key = (model._meta.app_label, model._meta.model_name)
        self.__class__._cache.setdefault(using, {})[key] = ct
        self.__class__._cache.setdefault(using, {})[ct.id] = ct

@python_2_unicode_compatible
class ContentType(models.Model):
    name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    model = models.CharField(_('python model class name'), max_length=100)
    objects = ContentTypeManager()

    class Meta:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        db_table = 'django_content_type'
        ordering = ('name',)
        unique_together = (('app_label', 'model'),)

    def __str__(self):
        # self.name is deprecated in favor of using model's verbose_name, which
        # can be translated. Formal deprecation is delayed until we have DB
        # migration to be able to remove the field from the database along with
        # the attribute.
        #
        # We return self.name only when users have changed its value from the
        # initial verbose_name_raw and might rely on it.
        model = self.model_class()
        if not model or self.name != model._meta.verbose_name_raw:
            return self.name
        else:
            return force_text(model._meta.verbose_name)

    def model_class(self):
        "Returns the Python model class for this type of content."
        from django.db import models
        return models.get_model(self.app_label, self.model,
                                only_installed=False)

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
