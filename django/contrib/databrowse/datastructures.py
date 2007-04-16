"""
These classes are light wrappers around Django's database API that provide
convenience functionality and permalink functions for the databrowse app.
"""

from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
from django.db import models
from django.utils import dateformat
from django.utils.text import capfirst
from django.utils.translation import get_date_formats

class EasyModel(object):
    def __init__(self, site, model):
        self.site = site
        self.model = model
        self.model_list = site.registry.keys()
        self.verbose_name = model._meta.verbose_name
        self.verbose_name_plural = model._meta.verbose_name_plural

    def __repr__(self):
        return '<EasyModel for %s>' % self.model._meta.object_name

    def model_databrowse(self):
        "Returns the ModelDatabrowse class for this model."
        return self.site.registry[self.model]

    def url(self):
        return '%s%s/%s/' % (self.site.root_url, self.model._meta.app_label, self.model._meta.module_name)

    def objects(self, **kwargs):
        for obj in self.model._default_manager.filter(**kwargs):
            yield EasyInstance(self, obj)

    def object_by_pk(self, pk):
        return EasyInstance(self, self.model._default_manager.get(pk=pk))

    def sample_objects(self):
        for obj in self.model._default_manager.all()[:3]:
            yield EasyInstance(self, obj)

    def field(self, name):
        try:
            f = self.model._meta.get_field(name)
        except models.FieldDoesNotExist:
            return None
        return EasyField(self, f)

    def fields(self):
        return [EasyField(self, f) for f in (self.model._meta.fields + self.model._meta.many_to_many)]

class EasyField(object):
    def __init__(self, easy_model, field):
        self.model, self.field = easy_model, field

    def __repr__(self):
        return '<EasyField for %s.%s>' % (self.model.model._meta.object_name, self.field.name)

    def choices(self):
        for value, label in self.field.choices:
            yield EasyChoice(self.model, self, value, label)

    def url(self):
        if self.field.choices:
            return '%s%s/%s/%s/' % (self.model.site.root_url, self.model.model._meta.app_label, self.model.model._meta.module_name, self.field.name)
        elif self.field.rel:
            return '%s%s/%s/' % (self.model.site.root_url, self.model.model._meta.app_label, self.model.model._meta.module_name)

class EasyChoice(object):
    def __init__(self, easy_model, field, value, label):
        self.model, self.field = easy_model, field
        self.value, self.label = value, label

    def __repr__(self):
        return '<EasyChoice for %s.%s>' % (self.model.model._meta.object_name, self.field.name)

    def url(self):
        return '%s%s/%s/%s/%s/' % (self.model.site.root_url, self.model.model._meta.app_label, self.model.model._meta.module_name, self.field.field.name, self.value)

class EasyInstance(object):
    def __init__(self, easy_model, instance):
        self.model, self.instance = easy_model, instance

    def __repr__(self):
        return '<EasyInstance for %s (%s)>' % (self.model.model._meta.object_name, self.instance._get_pk_val())

    def __str__(self):
        val = str(self.instance)
        if len(val) > 30:
            return val[:30] + '...'
        return val

    def pk(self):
        return self.instance._get_pk_val()

    def url(self):
        return '%s%s/%s/objects/%s/' % (self.model.site.root_url, self.model.model._meta.app_label, self.model.model._meta.module_name, self.pk())

    def fields(self):
        """
        Generator that yields EasyInstanceFields for each field in this
        EasyInstance's model.
        """
        for f in self.model.model._meta.fields + self.model.model._meta.many_to_many:
            yield EasyInstanceField(self.model, self, f)

    def related_objects(self):
        """
        Generator that yields dictionaries of all models that have this
        EasyInstance's model as a ForeignKey or ManyToManyField, along with
        lists of related objects.
        """
        for rel_object in self.model.model._meta.get_all_related_objects() + self.model.model._meta.get_all_related_many_to_many_objects():
            if rel_object.model not in self.model.model_list:
                continue # Skip models that aren't in the model_list
            em = EasyModel(self.model.site, rel_object.model)
            yield {
                'model': em,
                'related_field': rel_object.field.verbose_name,
                'object_list': [EasyInstance(em, i) for i in getattr(self.instance, rel_object.get_accessor_name()).all()],
            }

class EasyInstanceField(object):
    def __init__(self, easy_model, instance, field):
        self.model, self.field, self.instance = easy_model, field, instance
        self.raw_value = getattr(instance.instance, field.name)

    def __repr__(self):
        return '<EasyInstanceField for %s.%s>' % (self.model.model._meta.object_name, self.field.name)

    def values(self):
        """
        Returns a list of values for this field for this instance. It's a list
        so we can accomodate many-to-many fields.
        """
        if self.field.rel:
            if isinstance(self.field.rel, models.ManyToOneRel):
                objs = getattr(self.instance.instance, self.field.name)
            elif isinstance(self.field.rel, models.ManyToManyRel): # ManyToManyRel
                return list(getattr(self.instance.instance, self.field.name).all())
        elif self.field.choices:
            objs = dict(self.field.choices).get(self.raw_value, EMPTY_CHANGELIST_VALUE)
        elif isinstance(self.field, models.DateField) or isinstance(self.field, models.TimeField):
            if self.raw_value:
                date_format, datetime_format, time_format = get_date_formats()
                if isinstance(self.field, models.DateTimeField):
                    objs = capfirst(dateformat.format(self.raw_value, datetime_format))
                elif isinstance(self.field, models.TimeField):
                    objs = capfirst(dateformat.time_format(self.raw_value, time_format))
                else:
                    objs = capfirst(dateformat.format(self.raw_value, date_format))
            else:
                objs = EMPTY_CHANGELIST_VALUE
        elif isinstance(self.field, models.BooleanField) or isinstance(self.field, models.NullBooleanField):
            objs = {True: 'Yes', False: 'No', None: 'Unknown'}[self.raw_value]
        else:
            objs = self.raw_value
        return [objs]

    def urls(self):
        "Returns a list of (value, URL) tuples."
        # First, check the urls() method for each plugin.
        plugin_urls = []
        for plugin_name, plugin in self.model.model_databrowse().plugins.items():
            urls = plugin.urls(plugin_name, self)
            if urls is not None:
                #plugin_urls.append(urls)
                values = self.values()
                return zip(self.values(), urls)
        if self.field.rel:
            m = EasyModel(self.model.site, self.field.rel.to)
            if self.field.rel.to in self.model.model_list:
                lst = []
                for value in self.values():
                    url = '%s%s/%s/objects/%s/' % (self.model.site.root_url, m.model._meta.app_label, m.model._meta.module_name, value._get_pk_val())
                    lst.append((str(value), url))
            else:
                lst = [(value, None) for value in self.values()]
        elif self.field.choices:
            lst = []
            for value in self.values():
                url = '%s%s/%s/fields/%s/%s/' % (self.model.site.root_url, self.model.model._meta.app_label, self.model.model._meta.module_name, self.field.name, self.raw_value)
                lst.append((value, url))
        elif isinstance(self.field, models.URLField):
            val = self.values()[0]
            lst = [(val, val)]
        else:
            lst = [(self.values()[0], None)]
        return lst
