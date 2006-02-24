from django.db import models
from django.utils.translation import gettext_lazy as _

class Package(models.Model):
    label = models.CharField(_('label'), maxlength=20, primary_key=True)
    name = models.CharField(_('name'), maxlength=30, unique=True)
    class Meta:
        verbose_name = _('package')
        verbose_name_plural = _('packages')
        db_table = 'django_package'
        ordering = ('name',)

    def __repr__(self):
        return self.name

class ContentTypeManager(models.Manager):
    def get_for_model(self, model):
        """
        Returns the ContentType object for the given model, creating the
        ContentType if necessary.
        """
        opts = model._meta
        try:
            return self.model._default_manager.get(python_module_name__exact=opts.module_name,
                package__label__exact=opts.app_label)
        except self.model.DoesNotExist:
            # The str() is needed around opts.verbose_name because it's a
            # django.utils.functional.__proxy__ object.
            ct = self.model(name=str(opts.verbose_name),
                package=Package.objects.get(label=opts.app_label),
                python_module_name=opts.module_name)
            ct.save()
            return ct

class ContentType(models.Model):
    name = models.CharField(_('name'), maxlength=100)
    package = models.ForeignKey(Package, db_column='package')
    python_module_name = models.CharField(_('python module name'), maxlength=50)
    objects = ContentTypeManager()
    class Meta:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        db_table = 'django_content_type'
        ordering = ('package', 'name')
        unique_together = (('package', 'python_module_name'),)

    def __repr__(self):
        return "%s | %s" % (self.package_id, self.name)

    def get_model_module(self):
        "Returns the Python model module for accessing this type of content."
        return __import__('django.models.%s.%s' % (self.package_id, self.python_module_name), '', '', [''])

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.get_model_module().get_object(**kwargs)
