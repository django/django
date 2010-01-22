from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

class ContentTypeManager(models.Manager):

    # Cache to avoid re-looking up ContentType objects all over the place.
    # This cache is shared by all the get_for_* methods.
    _cache = {}

    def get_by_natural_key(self, app_label, model):
        try:
            ct = self.__class__._cache[self.db][(app_label, model)]
        except KeyError:
            ct = self.get(app_label=app_label, model=model)
        return ct

    def get_for_model(self, model):
        """
        Returns the ContentType object for a given model, creating the
        ContentType if necessary. Lookups are cached so that subsequent lookups
        for the same model don't hit the database.
        """
        opts = model._meta
        while opts.proxy:
            model = opts.proxy_for_model
            opts = model._meta
        key = (opts.app_label, opts.object_name.lower())
        try:
            ct = self.__class__._cache[self.db][key]
        except KeyError:
            # Load or create the ContentType entry. The smart_unicode() is
            # needed around opts.verbose_name_raw because name_raw might be a
            # django.utils.functional.__proxy__ object.
            ct, created = self.get_or_create(
                app_label = opts.app_label,
                model = opts.object_name.lower(),
                defaults = {'name': smart_unicode(opts.verbose_name_raw)},
            )
            self._add_to_cache(self.db, ct)

        return ct

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
        key = (model._meta.app_label, model._meta.object_name.lower())
        self.__class__._cache.setdefault(using, {})[key] = ct
        self.__class__._cache.setdefault(using, {})[ct.id] = ct

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

    def __unicode__(self):
        return self.name

    def model_class(self):
        "Returns the Python model class for this type of content."
        from django.db import models
        return models.get_model(self.app_label, self.model)

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.model_class()._default_manager.using(self._state.db).get(**kwargs)

    def natural_key(self):
        return (self.app_label, self.model)
