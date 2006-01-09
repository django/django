from django.db import models
from django.utils.translation import gettext_lazy as _

class Package(models.Model):
    label = models.CharField(_('label'), maxlength=20, primary_key=True)
    name = models.CharField(_('name'), maxlength=30, unique=True)
    class Meta:
        verbose_name = _('package')
        verbose_name_plural = _('packages')
        db_table = 'packages'
        ordering = ('name',)

    def __repr__(self):
        return self.name

class ContentType(models.Model):
    name = models.CharField(_('name'), maxlength=100)
    package = models.ForeignKey(Package, db_column='package')
    python_module_name = models.CharField(_('python module name'), maxlength=50)
    class Meta:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        db_table = 'content_types'
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
