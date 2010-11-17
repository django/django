import re
from bisect import bisect

from django.conf import settings
from django.db.models.related import RelatedObject
from django.db.models.fields.related import ManyToManyRel
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.proxy import OrderWrt
from django.db.models.loading import get_models, app_cache_ready
from django.utils.translation import activate, deactivate_all, get_language, string_concat
from django.utils.encoding import force_unicode, smart_str
from django.utils.datastructures import SortedDict

try:
    all
except NameError:
    from django.utils.itercompat import all

# Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
get_verbose_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', class_name).lower().strip()

DEFAULT_NAMES = ('verbose_name', 'verbose_name_plural', 'db_table', 'ordering',
                 'unique_together', 'permissions', 'get_latest_by',
                 'order_with_respect_to', 'app_label', 'db_tablespace',
                 'abstract', 'managed', 'proxy', 'auto_created')

class Options(object):
    def __init__(self, meta, app_label=None):
        self.local_fields, self.local_many_to_many = [], []
        self.virtual_fields = []
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.db_table = ''
        self.ordering = []
        self.unique_together =  []
        self.permissions =  []
        self.object_name, self.app_label = None, app_label
        self.get_latest_by = None
        self.order_with_respect_to = None
        self.db_tablespace = settings.DEFAULT_TABLESPACE
        self.admin = None
        self.meta = meta
        self.pk = None
        self.has_auto_field, self.auto_field = False, None
        self.abstract = False
        self.managed = True
        self.proxy = False
        self.proxy_for_model = None
        self.parents = SortedDict()
        self.duplicate_targets = {}
        self.auto_created = False

        # To handle various inheritance situations, we need to track where
        # managers came from (concrete or abstract base classes).
        self.abstract_managers = []
        self.concrete_managers = []

    def contribute_to_class(self, cls, name):
        from django.db import connection
        from django.db.backends.util import truncate_name

        cls._meta = self
        self.installed = re.sub('\.models$', '', cls.__module__) in settings.INSTALLED_APPS
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

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
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # unique_together can be either a tuple of tuples, or a single
            # tuple of two strings. Normalize it to a tuple of tuples, so that
            # calling code can uniformly expect that.
            ut = meta_attrs.pop('unique_together', self.unique_together)
            if ut and not isinstance(ut[0], (tuple, list)):
                ut = (ut,)
            self.unique_together = ut

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

        # If the db_table wasn't provided, use the app_label + module_name.
        if not self.db_table:
            self.db_table = "%s_%s" % (self.app_label, self.module_name)
            self.db_table = truncate_name(self.db_table, connection.ops.max_name_length())

    def _prepare(self, model):
        if self.order_with_respect_to:
            self.order_with_respect_to = self.get_field(self.order_with_respect_to)
            self.ordering = ('_order',)
            model.add_to_class('_order', OrderWrt())
        else:
            self.order_with_respect_to = None

        if self.pk is None:
            if self.parents:
                # Promote the first parent link in lieu of adding yet another
                # field.
                field = self.parents.value_for_index(0)
                field.primary_key = True
                self.setup_pk(field)
            else:
                auto = AutoField(verbose_name='ID', primary_key=True,
                        auto_created=True)
                model.add_to_class('id', auto)

        # Determine any sets of fields that are pointing to the same targets
        # (e.g. two ForeignKeys to the same remote model). The query
        # construction code needs to know this. At the end of this,
        # self.duplicate_targets will map each duplicate field column to the
        # columns it duplicates.
        collections = {}
        for column, target in self.duplicate_targets.iteritems():
            try:
                collections[target].add(column)
            except KeyError:
                collections[target] = set([column])
        self.duplicate_targets = {}
        for elt in collections.itervalues():
            if len(elt) == 1:
                continue
            for column in elt:
                self.duplicate_targets[column] = elt.difference(set([column]))

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
            if hasattr(self, '_field_cache'):
                del self._field_cache
                del self._field_name_cache

        if hasattr(self, '_name_map'):
            del self._name_map

    def add_virtual_field(self, field):
        self.virtual_fields.append(field)

    def setup_pk(self, field):
        if not self.pk and field.primary_key:
            self.pk = field
            field.serialize = False

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
        return "%s.%s" % (smart_str(self.app_label), smart_str(self.module_name))

    def verbose_name_raw(self):
        """
        There are a few places where the untranslated verbose name is needed
        (so that we get the same value regardless of currently active
        locale).
        """
        lang = get_language()
        deactivate_all()
        raw = force_unicode(self.verbose_name)
        activate(lang)
        return raw
    verbose_name_raw = property(verbose_name_raw)

    def _fields(self):
        """
        The getter for self.fields. This returns the list of field objects
        available to this model (including through parent models).

        Callers are not permitted to modify this list, since it's a reference
        to this instance (not a copy).
        """
        try:
            self._field_name_cache
        except AttributeError:
            self._fill_fields_cache()
        return self._field_name_cache
    fields = property(_fields)

    def get_fields_with_model(self):
        """
        Returns a sequence of (field, model) pairs for all fields. The "model"
        element is None for fields on the current model. Mostly of use when
        constructing queries so that we know which model a field belongs to.
        """
        try:
            self._field_cache
        except AttributeError:
            self._fill_fields_cache()
        return self._field_cache

    def _fill_fields_cache(self):
        cache = []
        for parent in self.parents:
            for field, model in parent._meta.get_fields_with_model():
                if model:
                    cache.append((field, model))
                else:
                    cache.append((field, parent))
        cache.extend([(f, None) for f in self.local_fields])
        self._field_cache = tuple(cache)
        self._field_name_cache = [x for x, _ in cache]

    def _many_to_many(self):
        try:
            self._m2m_cache
        except AttributeError:
            self._fill_m2m_cache()
        return self._m2m_cache.keys()
    many_to_many = property(_many_to_many)

    def get_m2m_with_model(self):
        """
        The many-to-many version of get_fields_with_model().
        """
        try:
            self._m2m_cache
        except AttributeError:
            self._fill_m2m_cache()
        return self._m2m_cache.items()

    def _fill_m2m_cache(self):
        cache = SortedDict()
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
        to_search = many_to_many and (self.fields + self.many_to_many) or self.fields
        for f in to_search:
            if f.name == name:
                return f
        raise FieldDoesNotExist('%s has no field named %r' % (self.object_name, name))

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
        try:
            try:
                return self._name_map[name]
            except AttributeError:
                cache = self.init_name_map()
                return cache[name]
        except KeyError:
            raise FieldDoesNotExist('%s has no field named %r'
                    % (self.object_name, name))

    def get_all_field_names(self):
        """
        Returns a list of all field names that are possible for this model
        (including reverse relation names). This is used for pretty printing
        debugging output (a list of choices), so any internal-only field names
        are not included.
        """
        try:
            cache = self._name_map
        except AttributeError:
            cache = self.init_name_map()
        names = cache.keys()
        names.sort()
        # Internal-only names end with "+" (symmetrical m2m related names being
        # the main example). Trim them.
        return [val for val in names if not val.endswith('+')]

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
            cache[f.name] = (f, model, True, True)
        for f, model in self.get_fields_with_model():
            cache[f.name] = (f, model, True, False)
        if app_cache_ready():
            self._name_map = cache
        return cache

    def get_add_permission(self):
        return 'add_%s' % self.object_name.lower()

    def get_change_permission(self):
        return 'change_%s' % self.object_name.lower()

    def get_delete_permission(self):
        return 'delete_%s' % self.object_name.lower()

    def get_all_related_objects(self, local_only=False, include_hidden=False):
        return [k for k, v in self.get_all_related_objects_with_model(
                local_only=local_only, include_hidden=include_hidden)]

    def get_all_related_objects_with_model(self, local_only=False,
                                           include_hidden=False):
        """
        Returns a list of (related-object, model) pairs. Similar to
        get_fields_with_model().
        """
        try:
            self._related_objects_cache
        except AttributeError:
            self._fill_related_objects_cache()
        predicates = []
        if local_only:
            predicates.append(lambda k, v: not v)
        if not include_hidden:
            predicates.append(lambda k, v: not k.field.rel.is_hidden())
        return filter(lambda t: all([p(*t) for p in predicates]),
                      self._related_objects_cache.items())

    def _fill_related_objects_cache(self):
        cache = SortedDict()
        parent_list = self.get_parent_list()
        for parent in self.parents:
            for obj, model in parent._meta.get_all_related_objects_with_model():
                if (obj.field.creation_counter < 0 or obj.field.rel.parent_link) and obj.model not in parent_list:
                    continue
                if not model:
                    cache[obj] = parent
                else:
                    cache[obj] = model
        for klass in get_models(include_auto_created=True):
            for f in klass._meta.local_fields:
                if f.rel and not isinstance(f.rel.to, str) and self == f.rel.to._meta:
                    cache[RelatedObject(f.rel.to, klass, f)] = None
        self._related_objects_cache = cache

    def get_all_related_many_to_many_objects(self, local_only=False):
        try:
            cache = self._related_many_to_many_cache
        except AttributeError:
            cache = self._fill_related_many_to_many_cache()
        if local_only:
            return [k for k, v in cache.items() if not v]
        return cache.keys()

    def get_all_related_m2m_objects_with_model(self):
        """
        Returns a list of (related-m2m-object, model) pairs. Similar to
        get_fields_with_model().
        """
        try:
            cache = self._related_many_to_many_cache
        except AttributeError:
            cache = self._fill_related_many_to_many_cache()
        return cache.items()

    def _fill_related_many_to_many_cache(self):
        cache = SortedDict()
        parent_list = self.get_parent_list()
        for parent in self.parents:
            for obj, model in parent._meta.get_all_related_m2m_objects_with_model():
                if obj.field.creation_counter < 0 and obj.model not in parent_list:
                    continue
                if not model:
                    cache[obj] = parent
                else:
                    cache[obj] = model
        for klass in get_models():
            for f in klass._meta.local_many_to_many:
                if f.rel and not isinstance(f.rel.to, str) and self == f.rel.to._meta:
                    cache[RelatedObject(f.rel.to, klass, f)] = None
        if app_cache_ready():
            self._related_many_to_many_cache = cache
        return cache

    def get_base_chain(self, model):
        """
        Returns a list of parent classes leading to 'model' (order from closet
        to most distant ancestor). This has to handle the case were 'model' is
        a granparent or even more distant relation.
        """
        if not self.parents:
            return
        if model in self.parents:
            return [model]
        for parent in self.parents:
            res = parent._meta.get_base_chain(model)
            if res:
                res.insert(0, parent)
                return res
        raise TypeError('%r is not an ancestor of this model'
                % model._meta.module_name)

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

    def get_ordered_objects(self):
        "Returns a list of Options objects that are ordered with respect to this object."
        if not hasattr(self, '_ordered_objects'):
            objects = []
            # TODO
            #for klass in get_models(get_app(self.app_label)):
            #    opts = klass._meta
            #    if opts.order_with_respect_to and opts.order_with_respect_to.rel \
            #        and self == opts.order_with_respect_to.rel.to._meta:
            #        objects.append(opts)
            self._ordered_objects = objects
        return self._ordered_objects

    def pk_index(self):
        """
        Returns the index of the primary key field in the self.fields list.
        """
        return self.fields.index(self.pk)
