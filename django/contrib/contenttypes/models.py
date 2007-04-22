from django.db import models
from django.utils.translation import gettext_lazy as _

CONTENT_TYPE_CACHE = {}
class ContentTypeManager(models.Manager):
    def get_for_model(self, model):
        """
        Returns the ContentType object for the given model, creating the
        ContentType if necessary.
        """
        opts = model._meta
        key = (opts.app_label, opts.object_name.lower())
        try:
            ct = CONTENT_TYPE_CACHE[key]
        except KeyError:
            # The str() is needed around opts.verbose_name because it's a
            # django.utils.functional.__proxy__ object.
            ct, created = self.model._default_manager.get_or_create(app_label=key[0],
                model=key[1], defaults={'name': str(opts.verbose_name)})
            CONTENT_TYPE_CACHE[key] = ct
        return ct
        
    def clear_cache(self):
        """
        Clear out the content-type cache. This needs to happen during database
        flushes to prevent caching of "stale" content type IDs (see
        django.contrib.contenttypes.management.create_contenttypes for where
        this gets called).
        """
        global CONTENT_TYPE_CACHE
        CONTENT_TYPE_CACHE = {}

class ContentType(models.Model):
    name = models.CharField(maxlength=100)
    app_label = models.CharField(maxlength=100)
    model = models.CharField(_('python model class name'), maxlength=100)
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
        return self.model_class()._default_manager.get(**kwargs)
