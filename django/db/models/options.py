import re
from bisect import bisect
try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

from django.conf import settings
from django.db.models.related import RelatedObject
from django.db.models.fields.related import ManyToManyRel
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.proxy import OrderWrt
from django.db.models.loading import get_models, app_cache_ready
from django.db.models import Manager
from django.utils.translation import activate, deactivate_all, get_language, string_concat
from django.utils.encoding import force_unicode, smart_str
from django.utils.datastructures import SortedDict

# Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
get_verbose_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', class_name).lower().strip()

DEFAULT_NAMES = ('verbose_name', 'db_table', 'ordering',
                 'unique_together', 'permissions', 'get_latest_by',
                 'order_with_respect_to', 'app_label', 'db_tablespace',
                 'abstract')

class Options(object):
    def __init__(self, meta):
        self.local_fields, self.local_many_to_many = [], []
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.db_table = ''
        self.ordering = []
        self.unique_together =  []
        self.permissions =  []
        self.object_name, self.app_label = None, None
        self.get_latest_by = None
        self.order_with_respect_to = None
        self.db_tablespace = settings.DEFAULT_TABLESPACE
        self.admin = None
        self.meta = meta
        self.pk = None
        self.has_auto_field, self.auto_field = False, None
        self.one_to_one_field = None
        self.abstract = False
        self.parents = SortedDict()

    def contribute_to_class(self, cls, name):
        cls._meta = self
        self.installed = re.sub('\.models$', '', cls.__module__) in settings.INSTALLED_APPS
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            del meta_attrs['__module__']
            del meta_attrs['__doc__']
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # unique_together can be either a tuple of tuples, or a single
            # tuple of two strings. Normalize it to a tuple of tuples, so that
            # calling code can uniformly expect that.
            ut = meta_attrs.pop('unique_together', getattr(self, 'unique_together'))
            if ut and not isinstance(ut[0], (tuple, list)):
                ut = (ut,)
            setattr(self, 'unique_together', ut)

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            setattr(self, 'verbose_name_plural', meta_attrs.pop('verbose_name_plural', string_concat(self.verbose_name, 's')))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError, "'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys())
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta

    def _prepare(self, model):
        from django.db import connection
        from django.db.backends.util import truncate_name
        if self.order_with_respect_to:
            self.order_with_respect_to = self.get_field(self.order_with_respect_to)
            self.ordering = ('_order',)
        else:
            self.order_with_respect_to = None

        if self.pk is None:
            if self.parents:
                # Promote the first parent link in lieu of adding yet another
                # field.
                field = self.parents.value_for_index(0)
                field.primary_key = True
                self.pk = field
            else:
                auto = AutoField(verbose_name='ID', primary_key=True,
                        auto_created=True)
                model.add_to_class('id', auto)

        # If the db_table wasn't provided, use the app_label + module_name.
        if not self.db_table:
            self.db_table = "%s_%s" % (self.app_label, self.module_name)
            self.db_table = truncate_name(self.db_table, connection.ops.max_name_length())

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

    def setup_pk(self, field):
        if not self.pk and field.primary_key:
            self.pk = field
            field.serialize = False

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
        raise FieldDoesNotExist, '%s has no field named %r' % (self.object_name, name)

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
        (including reverse relation names).
        """
        try:
            cache = self._name_map
        except AttributeError:
            cache = self.init_name_map()
        names = cache.keys()
        names.sort()
        return names

    def init_name_map(self):
        """
        Initialises the field name -> field object mapping.
        """
        cache = dict([(f.name, (f, m, True, False)) for f, m in
                self.get_fields_with_model()])
        for f, model in self.get_m2m_with_model():
            cache[f.name] = (f, model, True, True)
        for f, model in self.get_all_related_m2m_objects_with_model():
            cache[f.field.related_query_name()] = (f, model, False, True)
        for f, model in self.get_all_related_objects_with_model():
            cache[f.field.related_query_name()] = (f, model, False, False)
        if self.order_with_respect_to:
            cache['_order'] = OrderWrt(), None, True, False
        if app_cache_ready():
            self._name_map = cache
        return cache

    def get_add_permission(self):
        return 'add_%s' % self.object_name.lower()

    def get_change_permission(self):
        return 'change_%s' % self.object_name.lower()

    def get_delete_permission(self):
        return 'delete_%s' % self.object_name.lower()

    def get_all_related_objects(self, local_only=False):
        try:
            self._related_objects_cache
        except AttributeError:
            self._fill_related_objects_cache()
        if local_only:
            return [k for k, v in self._related_objects_cache.items() if not v]
        return self._related_objects_cache.keys()

    def get_all_related_objects_with_model(self):
        """
        Returns a list of (related-object, model) pairs. Similar to
        get_fields_with_model().
        """
        try:
            self._related_objects_cache
        except AttributeError:
            self._fill_related_objects_cache()
        return self._related_objects_cache.items()

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
        for klass in get_models():
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

    def get_followed_related_objects(self, follow=None):
        if follow == None:
            follow = self.get_follow()
        return [f for f in self.get_all_related_objects() if follow.get(f.name, None)]

    def get_data_holders(self, follow=None):
        if follow == None:
            follow = self.get_follow()
        return [f for f in self.fields + self.many_to_many + self.get_all_related_objects() if follow.get(f.name, None)]

    def get_follow(self, override=None):
        follow = {}
        for f in self.fields + self.many_to_many + self.get_all_related_objects():
            if override and f.name in override:
                child_override = override[f.name]
            else:
                child_override = None
            fol = f.get_follow(child_override)
            if fol != None:
                follow[f.name] = fol
        return follow

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

    def has_field_type(self, field_type, follow=None):
        """
        Returns True if this object's admin form has at least one of the given
        field_type (e.g. FileField).
        """
        # TODO: follow
        if not hasattr(self, '_field_types'):
            self._field_types = {}
        if field_type not in self._field_types:
            try:
                # First check self.fields.
                for f in self.fields:
                    if isinstance(f, field_type):
                        raise StopIteration
                # Failing that, check related fields.
                for related in self.get_followed_related_objects(follow):
                    for f in related.opts.fields:
                        if isinstance(f, field_type):
                            raise StopIteration
            except StopIteration:
                self._field_types[field_type] = True
            else:
                self._field_types[field_type] = False
        return self._field_types[field_type]

class AdminOptions(object):
    def __init__(self, fields=None, js=None, list_display=None, list_display_links=None, list_filter=None,
        date_hierarchy=None, save_as=False, ordering=None, search_fields=None,
        save_on_top=False, list_select_related=False, manager=None, list_per_page=100):
        self.fields = fields
        self.js = js or []
        self.list_display = list_display or ['__str__']
        self.list_display_links = list_display_links or []
        self.list_filter = list_filter or []
        self.date_hierarchy = date_hierarchy
        self.save_as, self.ordering = save_as, ordering
        self.search_fields = search_fields or []
        self.save_on_top = save_on_top
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.manager = manager or Manager()

    def get_field_sets(self, opts):
        "Returns a list of AdminFieldSet objects for this AdminOptions object."
        if self.fields is None:
            field_struct = ((None, {'fields': [f.name for f in opts.fields + opts.many_to_many if f.editable and not isinstance(f, AutoField)]}),)
        else:
            field_struct = self.fields
        new_fieldset_list = []
        for fieldset in field_struct:
            fs_options = fieldset[1]
            classes = fs_options.get('classes', ())
            description = fs_options.get('description', '')
            new_fieldset_list.append(AdminFieldSet(fieldset[0], classes,
                opts.get_field, fs_options['fields'], description))
        return new_fieldset_list

    def contribute_to_class(self, cls, name):
        cls._meta.admin = self
        # Make sure the admin manager has access to the model
        self.manager.model = cls

class AdminFieldSet(object):
    def __init__(self, name, classes, field_locator_func, line_specs, description):
        self.name = name
        self.field_lines = [AdminFieldLine(field_locator_func, line_spec) for line_spec in line_specs]
        self.classes = classes
        self.description = description

    def __repr__(self):
        return "FieldSet: (%s, %s)" % (self.name, self.field_lines)

    def bind(self, field_mapping, original, bound_field_set_class):
        return bound_field_set_class(self, field_mapping, original)

    def __iter__(self):
        for field_line in self.field_lines:
            yield field_line

    def __len__(self):
        return len(self.field_lines)

class AdminFieldLine(object):
    def __init__(self, field_locator_func, linespec):
        if isinstance(linespec, basestring):
            self.fields = [field_locator_func(linespec)]
        else:
            self.fields = [field_locator_func(field_name) for field_name in linespec]

    def bind(self, field_mapping, original, bound_field_line_class):
        return bound_field_line_class(self, field_mapping, original)

    def __iter__(self):
        for field in self.fields:
            yield field

    def __len__(self):
        return len(self.fields)
