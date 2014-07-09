from __future__ import unicode_literals

from bisect import bisect
from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.db.models.fields.related import ManyToManyRel, ManyToManyField
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.proxy import OrderWrt
from django.utils import six
from django.utils.encoding import force_text, smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.text import camel_case_to_spaces
from django.utils.translation import activate, deactivate_all, get_language, string_concat

from django.db.models.fields import Field


DEFAULT_NAMES = ('verbose_name', 'verbose_name_plural', 'db_table', 'ordering',
                 'unique_together', 'permissions', 'get_latest_by',
                 'order_with_respect_to', 'app_label', 'db_tablespace',
                 'abstract', 'managed', 'proxy', 'swappable', 'auto_created',
                 'index_together', 'apps', 'default_permissions',
                 'select_on_save', 'default_related_name')


def normalize_together(option_together):
    """
    option_together can be either a tuple of tuples, or a single
    tuple of two strings. Normalize it to a tuple of tuples, so that
    calling code can uniformly expect that.
    """
    try:
        if not option_together:
            return ()
        if not isinstance(option_together, (tuple, list)):
            raise TypeError
        first_element = next(iter(option_together))
        if not isinstance(first_element, (tuple, list)):
            option_together = (option_together,)
        # Normalize everything to tuples
        return tuple(tuple(ot) for ot in option_together)
    except TypeError:
        # If the value of option_together isn't valid, return it
        # verbatim; this will be picked up by the check framework later.
        return option_together


@python_2_unicode_compatible
class Options(object):
    def __init__(self, meta, app_label=None):
        self._map_details_cache = {}
        self._map_model_cache = {}
        self._get_new_fields_cache = {}
        self._get_new_field_cache = {}
        self.local_fields = []
        self.local_many_to_many = []
        self.virtual_fields = []
        self.model_name = None
        self.verbose_name = None
        self.verbose_name_plural = None
        self.db_table = ''
        self.ordering = []
        self.unique_together = []
        self.index_together = []
        self.select_on_save = False
        self.default_permissions = ('add', 'change', 'delete')
        self.permissions = []
        self.object_name = None
        self.app_label = app_label
        self.get_latest_by = None
        self.order_with_respect_to = None
        self.db_tablespace = settings.DEFAULT_TABLESPACE
        self.meta = meta
        self.pk = None
        self.has_auto_field = False
        self.auto_field = None
        self.abstract = False
        self.managed = True
        self.proxy = False
        # For any class that is a proxy (including automatically created
        # classes for deferred object loading), proxy_for_model tells us
        # which class this model is proxying. Note that proxy_for_model
        # can create a chain of proxy models. For non-proxy models, the
        # variable is always None.
        self.proxy_for_model = None
        # For any non-abstract class, the concrete class is the model
        # in the end of the proxy_for_model chain. In particular, for
        # concrete models, the concrete_model is always the class itself.
        self.concrete_model = None
        self.swappable = None
        self.parents = OrderedDict()
        self.auto_created = False

        # To handle various inheritance situations, we need to track where
        # managers came from (concrete or abstract base classes).
        self.abstract_managers = []
        self.concrete_managers = []

        # List of all lookups defined in ForeignKey 'limit_choices_to' options
        # from *other* models. Needed for some admin checks. Internal use only.
        self.related_fkey_lookups = []

        # A custom app registry to use, if you're making a separate model set.
        self.apps = apps

        self.default_related_name = None

    @property
    def app_config(self):
        # Don't go through get_app_config to avoid triggering imports.
        return self.apps.app_configs.get(self.app_label)

    @property
    def installed(self):
        return self.app_config is not None

    def get_new_field(self, field_name, m2m=True, data=True, related_objects=False, related_m2m=False, virtual=True):

        cache_key = (m2m, data, related_objects, related_m2m, virtual,)
        try:
            field_map = self._get_new_field_cache[cache_key]
        except KeyError:
            res = {}
            for field, names in six.iteritems(self.get_new_fields(m2m=m2m, data=data,
                                              related_objects=related_objects, related_m2m=related_m2m,
                                              virtual=virtual, recursive=True)):
                for name in names:
                    res[name] = field
            field_map = self._get_new_field_cache[cache_key] = res
        try:
            return field_map[field_name]
        except KeyError:
            raise FieldDoesNotExist('%s has no field named %r' % (self.object_name, field_name))

    def get_new_fields(self, m2m=False, data=True, related_m2m=False, related_objects=False, virtual=False,
                       include_parents=True, include_non_concrete=True, include_hidden=False, include_proxy=False, recursive=False):

        cache_key = (m2m, data, related_m2m, related_objects, virtual, include_parents,
                     include_non_concrete, include_hidden, include_proxy, recursive)
        try:
            return self._get_new_fields_cache[cache_key]
        except KeyError:
            pass

        fields = OrderedDict()
        options = {'include_parents': include_parents,
                   'include_non_concrete': include_non_concrete,
                   'include_hidden': include_hidden,
                   'include_proxy': include_proxy}

        if related_m2m:
            if include_parents:
                for parent in self.parents:
                    for obj, query_name in six.iteritems(parent._meta.get_new_fields(data=False, related_m2m=True,
                                                         **dict(options, recursive=True))):
                        is_valid = not (obj.field.creation_counter < 0
                                    and obj.model not in self.get_parent_list())
                        if is_valid:
                            fields[obj] = query_name

            for model in self.apps.non_swapped_models:
                for f in model._meta.many_to_many:
                    has_rel_attr = f.rel and not isinstance(f.rel.to, six.string_types)
                    if has_rel_attr and self == f.rel.to._meta:
                        fields[f.related] = (f.related_query_name(),)

        if related_objects:
            parent_list = self.get_parent_list()
            if include_parents:
                for parent in self.parents:
                    for obj, query_name in six.iteritems(parent._meta.get_new_fields(data=False, related_objects=True,
                                                         **dict(options, recursive=True, include_hidden=True))):
                        if not ((obj.field.creation_counter < 0
                                or obj.field.rel.parent_link)
                                and obj.model not in parent_list):
                            if include_hidden or not obj.field.rel.is_hidden():
                                fields[obj] = query_name

            for model in self.apps.non_swapped_models_auto_created:
                for f in model._meta.fields + model._meta.virtual_fields:
                    try:
                        if f.rel and f.has_class_relation:
                            to_meta = f.rel.to._meta
                            if (to_meta == self) or (include_proxy and self.concrete_model == to_meta.concrete_model):
                                if include_hidden or not f.related.field.rel.is_hidden():
                                    fields[f.related] = (f.related_query_name(),)
                    except AttributeError:
                        continue

        if m2m:
            if include_parents:
                for parent in self.parents:
                    fields.update(parent._meta.get_new_fields(data=False, m2m=True, **dict(options, recursive=True)))
            fields.update((field, (field.name, field.attname)) for field in self.local_many_to_many)

        if data:
            if include_parents:
                for parent in self.parents:
                    fields.update(parent._meta.get_new_fields(**dict(options, recursive=True)))
            for field in self.local_fields:
                if include_non_concrete or field.column is not None:
                    fields[field] = (field.name, field.attname)

        if virtual:
            for field in self.virtual_fields:
                fields[field] = (field.name,)

        if not recursive:
            fields = tuple(fields.keys())

        self._get_new_fields_cache[cache_key] = fields
        return fields

    def contribute_to_class(self, cls, name):
        from django.db import connection
        from django.db.backends.utils import truncate_name

        cls._meta = self
        self.model = cls
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.model_name = self.object_name.lower()
        self.verbose_name = camel_case_to_spaces(self.object_name)

        # Store the original user-defined values for each option,
        # for use when serializing the model definition
        self.original_attrs = {}

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                    self.original_attrs[attr_name] = getattr(self, attr_name)
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))
                    self.original_attrs[attr_name] = getattr(self, attr_name)

            ut = meta_attrs.pop('unique_together', self.unique_together)
            self.unique_together = normalize_together(ut)

            it = meta_attrs.pop('index_together', self.index_together)
            self.index_together = normalize_together(it)

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            if self.verbose_name_plural is None:
                self.verbose_name_plural = string_concat(self.verbose_name, 's')

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta

        # If the db_table wasn't provided, use the app_label + model_name.
        if not self.db_table:
            self.db_table = "%s_%s" % (self.app_label, self.model_name)
            self.db_table = truncate_name(self.db_table, connection.ops.max_name_length())

    def _prepare(self, model):
        if self.order_with_respect_to:
            self.order_with_respect_to = self.get_field(self.order_with_respect_to)
            self.ordering = ('_order',)
            if not any(isinstance(field, OrderWrt) for field in model._meta.local_fields):
                model.add_to_class('_order', OrderWrt())
        else:
            self.order_with_respect_to = None

        if self.pk is None:
            if self.parents:
                # Promote the first parent link in lieu of adding yet another
                # field.
                field = next(six.itervalues(self.parents))
                # Look for a local field with the same name as the
                # first parent link. If a local field has already been
                # created, use it instead of promoting the parent
                already_created = [fld for fld in self.local_fields if fld.name == field.name]
                if already_created:
                    field = already_created[0]
                field.primary_key = True
                self.setup_pk(field)
            else:
                auto = AutoField(verbose_name='ID', primary_key=True,
                        auto_created=True)
                model.add_to_class('id', auto)

    def _expire_cache(self):
        for cache_key in ('fields', 'concrete_fields', 'local_concrete_fields', 'field_names',):
            try:
                delattr(self, cache_key)
            except AttributeError:
                pass
        self._get_new_field_cache = {}
        self._get_new_fields_cache = {}

    def add_field(self, field):
        # Insert the given field in the order in which it was created, using
        # the "creation_counter" attribute of the field.
        # Move many-to-many related fields from self.fields into
        # self.many_to_many.
        if field.rel and isinstance(field.rel, ManyToManyRel):
            self.local_many_to_many.insert(bisect(self.local_many_to_many, field), field)
            if hasattr(self, '_m2m_cache'):
                del self._m2m_cache
        else:
            self.local_fields.insert(bisect(self.local_fields, field), field)
            self.setup_pk(field)
        self._expire_cache()

    def add_virtual_field(self, field):
        self.virtual_fields.append(field)
        self._expire_cache()

    def setup_pk(self, field):
        if not self.pk and field.primary_key:
            self.pk = field
            field.serialize = False

    def pk_index(self):
        """
        Returns the index of the primary key field in the self.concrete_fields
        list.
        """
        return self.concrete_fields.index(self.pk)

    def setup_proxy(self, target):
        """
        Does the internal setup so that the current model is a proxy for
        "target".
        """
        self.pk = target._meta.pk
        self.proxy_for_model = target
        self.db_table = target._meta.db_table

    def __repr__(self):
        return '<Options for %s>' % self.object_name

    def __str__(self):
        return "%s.%s" % (smart_text(self.app_label), smart_text(self.model_name))

    def verbose_name_raw(self):
        """
        There are a few places where the untranslated verbose name is needed
        (so that we get the same value regardless of currently active
        locale).
        """
        lang = get_language()
        deactivate_all()
        raw = force_text(self.verbose_name)
        activate(lang)
        return raw
    verbose_name_raw = property(verbose_name_raw)

    def _swapped(self):
        """
        Has this model been swapped out for another? If so, return the model
        name of the replacement; otherwise, return None.

        For historical reasons, model name lookups using get_model() are
        case insensitive, so we make sure we are case insensitive here.
        """
        if self.swappable:
            model_label = '%s.%s' % (self.app_label, self.model_name)
            swapped_for = getattr(settings, self.swappable, None)
            if swapped_for:
                try:
                    swapped_label, swapped_object = swapped_for.split('.')
                except ValueError:
                    # setting not in the format app_label.model_name
                    # raising ImproperlyConfigured here causes problems with
                    # test cleanup code - instead it is raised in get_user_model
                    # or as part of validation.
                    return swapped_for

                if '%s.%s' % (swapped_label, swapped_object.lower()) not in (None, model_label):
                    return swapped_for
        return None
    swapped = property(_swapped)

    @cached_property
    def fields(self):
        """
        The getter for self.fields. This returns the list of field objects
        available to this model (including through parent models).

        Callers are not permitted to modify this list, since it's a reference
        to this instance (not a copy).
        """
        return list(self.get_new_fields())

    @cached_property
    def concrete_fields(self):
        return list(self.get_new_fields(include_non_concrete=False))

    @cached_property
    def local_concrete_fields(self):
        return self.get_new_fields(include_parents=False, include_non_concrete=False)

    def get_fields_with_model(self):
        """
        Returns a sequence of (field, model) pairs for all fields. The "model"
        element is None for fields on the current model. Mostly of use when
        constructing queries so that we know which model a field belongs to.
        """
        return list(map(self._map_model, self.get_new_fields()))

    def get_concrete_fields_with_model(self):
        return list(map(self._map_model, self.get_new_fields(include_non_concrete=False)))

    def _fill_fields_cache(self):
        cache = []
        for parent in self.parents:
            for field, model in parent._meta.get_fields_with_model():
                if model:
                    cache.append((field, model))
                else:
                    cache.append((field, parent))
        cache.extend((f, None) for f in self.local_fields)
        self._field_cache = tuple(cache)
        self._field_name_cache = [x for x, _ in cache]

    @cached_property
    def many_to_many(self):
        return list(self.get_new_fields(data=False, m2m=True))

    @cached_property
    def field_names(self):
        res = set()
        for _, names in six.iteritems(self.get_new_fields(m2m=True, related_objects=True,
                                          related_m2m=True, virtual=True, recursive=True)):
            res.update(name for name in names if not name.endswith('+'))
        return list(res)

    def get_m2m_with_model(self):
        """
        The many-to-many version of get_fields_with_model().
        """
        return list(map(self._map_model, self.get_new_fields(data=False, m2m=True)))

    def _fill_m2m_cache(self):
        cache = OrderedDict()
        for parent in self.parents:
            for field, model in parent._meta.get_m2m_with_model():
                if model:
                    cache[field] = model
                else:
                    cache[field] = parent
        for field in self.local_many_to_many:
            cache[field] = None
        self._m2m_cache = cache

    def get_field(self, name, many_to_many=True):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        return self.get_new_field(name)

    def get_field_by_name(self, name):
        """
        Returns the (field_object, model, direct, m2m), where field_object is
        the Field instance for the given name, model is the model containing
        this field (None for local fields), direct is True if the field exists
        on this model, and m2m is True for many-to-many relations. When
        'direct' is False, 'field_object' is the corresponding RelatedObject
        for this field (since the field doesn't have an instance associated
        with it).

        Uses a cache internally, so after the first access, this is very fast.
        """
        return self._map_details(self.get_new_field(name, m2m=True, related_objects=True,
                                 related_m2m=True, virtual=True))

    def get_all_field_names(self):
        """
        Returns a list of all field names that are possible for this model
        (including reverse relation names). This is used for pretty printing
        debugging output (a list of choices), so any internal-only field names
        are not included.
        """
        return self.field_names

    def init_name_map(self):
        """
        Initialises the field name -> field object mapping.
        """
        cache = {}
        # We intentionally handle related m2m objects first so that symmetrical
        # m2m accessor names can be overridden, if necessary.
        for f, model in self.get_all_related_m2m_objects_with_model():
            cache[f.field.related_query_name()] = (f, model, False, True)
        for f, model in self.get_all_related_objects_with_model():
            cache[f.field.related_query_name()] = (f, model, False, False)
        for f, model in self.get_m2m_with_model():
            cache[f.name] = cache[f.attname] = (f, model, True, True)
        for f, model in self.get_fields_with_model():
            cache[f.name] = cache[f.attname] = (f, model, True, False)
        for f in self.virtual_fields:
            cache[f.name] = (f, None if f.model == self.model else f.model, True, False)
        if apps.ready:
            self._name_map = cache
        return cache

    def get_all_related_objects(self, local_only=False, include_hidden=False,
                                include_proxy_eq=False):
        include_parents = local_only is False
        return list(self.get_new_fields(data=False, related_objects=True,
                    include_parents=include_parents, include_hidden=include_hidden,
                    include_proxy=include_proxy_eq))

    def get_all_related_objects_with_model(self, local_only=False,
                                           include_hidden=False,
                                           include_proxy_eq=False):
        """
        Returns a list of (related-object, model) pairs. Similar to
        get_fields_with_model().
        """
        include_parents = local_only is False
        fields = self.get_new_fields(data=False, related_objects=True,
                            include_parents=include_parents, include_hidden=include_hidden,
                            include_proxy=include_proxy_eq)
        return list(map(self._map_model, fields))

    def _fill_related_objects_cache(self):
        cache = OrderedDict()
        parent_list = self.get_parent_list()
        for parent in self.parents:
            # For each parent, recursively call this fn
            for obj, model in parent._meta.get_all_related_objects_with_model(include_hidden=True):
                # If model is invalid, continue
                if (obj.field.creation_counter < 0 or obj.field.rel.parent_link) and obj.model not in parent_list:
                    continue

                # Add model to cache
                if not model:
                    cache[obj] = parent
                else:
                    cache[obj] = model

        # Collect also objects which are in relation to some proxy child/parent of self.
        proxy_cache = cache.copy()
        for klass in self.apps.get_models(include_auto_created=True):
            if not klass._meta.swapped:
                for f in klass._meta.local_fields + klass._meta.virtual_fields:
                    if (hasattr(f, 'rel') and f.rel and not isinstance(f.rel.to, six.string_types)
                            and f.generate_reverse_relation):
                        # If its on the same model
                        if self == f.rel.to._meta:
                            cache[f.related] = None
                            proxy_cache[f.related] = None
                        # If its on another model
                        elif self.concrete_model == f.rel.to._meta.concrete_model:
                            proxy_cache[f.related] = None

        # Only return direct related links
        self._related_objects_cache = cache
        self._related_objects_proxy_cache = proxy_cache

    def get_all_related_many_to_many_objects(self, local_only=False):
        return list(self.get_new_fields(data=False, related_m2m=True, include_parents=local_only is not True))

    def _map_model(self, connection):
        try:
            return connection, self._map_model_cache[connection]
        except KeyError:
            direct = isinstance(connection, Field) or hasattr(connection, 'is_gfk')
            model = connection.model if direct else connection.parent_model._meta.concrete_model
            if model == self.model:
                model = None

            self._map_model_cache[connection] = model
        return connection, model

    def _map_details(self, connection):
        try:
            model, direct, m2m = self._map_details_cache[connection]
            return connection, model, direct, m2m
        except KeyError:
            direct = isinstance(connection, Field) or hasattr(connection, 'is_gfk')
            model = connection.model if direct else connection.parent_model._meta.concrete_model
            if model == self.model:
                model = None

            field = connection if direct else connection.field
            m2m = isinstance(field, ManyToManyField)
            self._map_details_cache[connection] = model, direct, m2m
        return connection, model, direct, m2m

    def get_all_related_m2m_objects_with_model(self):
        """
        Returns a list of (related-m2m-object, model) pairs. Similar to
        get_fields_with_model().
        """
        return list(map(self._map_model, self.get_new_fields(data=False, related_m2m=True)))

    def _fill_related_many_to_many_cache(self):
        cache = OrderedDict()
        parent_list = self.get_parent_list()
        for parent in self.parents:
            for obj, model in parent._meta.get_all_related_m2m_objects_with_model():
                if obj.field.creation_counter < 0 and obj.model not in parent_list:
                    continue
                if not model:
                    cache[obj] = parent
                else:
                    cache[obj] = model
        for klass in self.apps.get_models():
            if not klass._meta.swapped:
                for f in klass._meta.local_many_to_many:
                    if (f.rel
                            and not isinstance(f.rel.to, six.string_types)
                            and self == f.rel.to._meta):
                        cache[f.related] = None
        if apps.ready:
            self._related_many_to_many_cache = cache
        return cache

    def get_base_chain(self, model):
        """
        Returns a list of parent classes leading to 'model' (order from closet
        to most distant ancestor). This has to handle the case were 'model' is
        a grandparent or even more distant relation.
        """
        if not self.parents:
            return None
        if model in self.parents:
            return [model]
        for parent in self.parents:
            res = parent._meta.get_base_chain(model)
            if res:
                res.insert(0, parent)
                return res
        return None

    def get_parent_list(self):
        """
        Returns a list of all the ancestor of this model as a list. Useful for
        determining if something is an ancestor, regardless of lineage.
        """
        result = set()
        for parent in self.parents:
            result.add(parent)
            result.update(parent._meta.get_parent_list())
        return result

    def get_ancestor_link(self, ancestor):
        """
        Returns the field on the current model which points to the given
        "ancestor". This is possible an indirect link (a pointer to a parent
        model, which points, eventually, to the ancestor). Used when
        constructing table joins for model inheritance.

        Returns None if the model isn't an ancestor of this one.
        """
        if ancestor in self.parents:
            return self.parents[ancestor]
        for parent in self.parents:
            # Tries to get a link field from the immediate parent
            parent_link = parent._meta.get_ancestor_link(ancestor)
            if parent_link:
                # In case of a proxied model, the first link
                # of the chain to the ancestor is that parent
                # links
                return self.parents[parent] or parent_link
