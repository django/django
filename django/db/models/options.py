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
        self._get_fields_cache = {}
        self._get_field_cache = {}
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

    ### INTERNAL METHODS AND PROPERTIES GO BELOW THIS LINE ###

    @property
    def app_config(self):
        # Don't go through get_app_config to avoid triggering imports.
        return self.apps.app_configs.get(self.app_label)

    @property
    def installed(self):
        return self.app_config is not None

    @property
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

    @property
    def swapped(self):
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

    def add_field(self, field, virtual=False):
        # Insert the given field in the order in which it was created, using
        # the "creation_counter" attribute of the field.
        # Move many-to-many related fields from self.fields into
        # self.many_to_many.
        if virtual:
            self.virtual_fields.append(field)

        elif field.rel and isinstance(field.rel, ManyToManyRel):
            self.local_many_to_many.insert(bisect(self.local_many_to_many, field), field)
        else:
            self.local_fields.insert(bisect(self.local_fields, field), field)
            self.setup_pk(field)
        self._expire_cache()

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
        self._get_field_cache = {}
        self._get_fields_cache = {}

    def __repr__(self):
        return '<Options for %s>' % self.object_name

    def __str__(self):
        return "%s.%s" % (smart_text(self.app_label), smart_text(self.model_name))

    ### PUBLICLY USABLE AND STABLE APIS GO BELOW THIS LINE ###

    def get_field(self, field_name, m2m=True, data=True, related_objects=False, related_m2m=False, virtual=True, **kwargs):
        """
        Returns a field instance given a field name. By default will only search in data and
        many to many fields. This can be changed by enabling or disabling field types using
        the flags available. Hidden or proxy fields cannot be retreived.

        Fields can be any of the following:
        - data:             any field that has an entry on the database
        - m2m:              a ManyToManyField defined on the current model
        - related_objects:  a one-to-many relation from another model that points to the current model
        - related_m2m:      a M2M relation from another model that points to the current model
        - virtual:          fields that do not necessarily have an entry on the database (like GenericForeignKey)
        """
        # NOTE: previous get_field API had a many_to_many key. This key
        # has now become m2m. In order to avoid breaking other's implementation
        # we will catch the use of 'many_to_many' key and convert it to m2m.
        try:
            m2m = kwargs['many_to_many']
        except KeyError:
            pass

        # Creates a cache key composed of all arguments
        cache_key = (m2m, data, related_objects, related_m2m, virtual,)

        try:
            field_map = self._get_field_cache[cache_key]
        except KeyError:
            res = {}

            # Call get_fields with export_name_map=True in order to have a field_instance -> names map
            for field, names in six.iteritems(self.get_fields(m2m=m2m, data=data,
                  related_objects=related_objects, related_m2m=related_m2m,
                  virtual=virtual, export_name_map=True)):
                # Map each possible name for a field to it's field instance
                for name in names:
                    res[name] = field

            field_map = self._get_field_cache[cache_key] = res
        try:
            # Retreive field instance by name from cached or just-computer field map
            return field_map[field_name]
        except KeyError:
            raise FieldDoesNotExist('%s has no field named %r' % (self.object_name, field_name))

    def get_fields(self, m2m=False, data=True, related_m2m=False, related_objects=False, virtual=False,
                   include_parents=True, include_non_concrete=True, include_hidden=False, include_proxy=False, export_name_map=False):
        """
        Returns a list of fields associated to the model. By default will only search in data.
        This can be changed by enabling or disabling field types using
        the flags available.

        Fields can be any of the following:
        - data:             any field that has an entry on the database
        - m2m:              a ManyToManyField defined on the current model
        - related_objects:  a one-to-many relation from another model that points to the current model
        - related_m2m:      a M2M relation from another model that points to the current model
        - virtual:          fields that do not necessarily have an entry on the database (like GenericForeignKey)

        Options can be any of the following:
        - include_parents:        include fields derived from inheritance
        - include_hidden:         include fields that have a related_name that starts with a "+"
        - include_non_concrete:   include fields that do not have a column
        - include_proxy:          include relations that point to a proxy of the model.
        """

        # Creates a cache key composed of all arguments
        cache_key = (m2m, data, related_m2m, related_objects, virtual, include_parents,
                     include_non_concrete, include_hidden, include_proxy, export_name_map)

        try:
            return self._get_fields_cache[cache_key]
        except KeyError:
            pass

        # Using an OrderedDict to preserve the order of insertion. This is fundamental
        # when displaying a ModelForm or django.contrib.admin panel and no specific ordering
        # is provided. For this reason, order of field insertion must be preserved
        fields = OrderedDict()
        options = {'include_parents': include_parents,
                   'include_non_concrete': include_non_concrete,
                   'include_hidden': include_hidden,
                   'include_proxy': include_proxy}

        if related_m2m:
            if include_parents:
                # Recursively call get_fields on each parent, with the same options provided
                # in this call
                for parent in self.parents:
                    for obj, query_name in six.iteritems(parent._meta.get_fields(data=False, related_m2m=True,
                                                         **dict(options, export_name_map=True))):
                        # In order for a related M2M object to be valid, it's creation
                        # counter must be > 0 and must be in the parent list
                        if not (obj.field.creation_counter < 0
                                and obj.model not in self.get_parent_list()):
                            fields[obj] = query_name

            # Tree is computer once and cached until apps cache is expired. It is composed of
            # { options_instance : [field_pointing_to_options_model, field_pointing_to_options, ..]}
            # If the model is a proxy model, then we also add the concrete model.
            tree = self.apps.related_m2m_relation_graph
            for f in tree[self] if not self.proxy else tree[self] + tree[self.concrete_model._meta]:
                fields[f.related] = (f.related_query_name(),)

        if related_objects:
            parent_list = self.get_parent_list()
            if include_parents:
                # Recursively call get_fields on each parent, with the same options provided
                # in this call
                for parent in self.parents:
                    for obj, query_name in six.iteritems(parent._meta.get_fields(data=False, related_objects=True,
                                                         **dict(options, export_name_map=True, include_hidden=True))):
                        if not ((obj.field.creation_counter < 0
                                or obj.field.rel.parent_link)
                                and obj.model not in parent_list):
                            if include_hidden or not obj.field.rel.is_hidden():
                                # If hidden fields should be included or the relation
                                # is not intentionally hidden, add to the fields dict
                                fields[obj] = query_name

            # Tree is computer once and cached until apps cache is expired. It is composed of
            # { options_instance : [field_pointing_to_options_model, field_pointing_to_options, ..]}
            # If the model is a proxy model, then we also add the concrete model.
            tree, proxy_tree = self.apps.related_objects_relation_graph
            all_fields = tree[self] if not self.proxy else tree[self] + tree[self.concrete_model._meta]
            if include_proxy:
                # If we are also incluing proxied relations, also add contents in the proxy tree.
                all_fields += proxy_tree[self.concrete_model]
            for f in all_fields:
                if include_hidden or not f.related.field.rel.is_hidden():
                    # If hidden fields should be included or the relation
                    # is not intentionally hidden, add to the fields dict
                    fields[f.related] = (f.related_query_name(),)

        if m2m:
            if include_parents:
                for parent in self.parents:
                    # Extend the fields dict with all the m2m fields of each parent.
                    fields.update(parent._meta.get_fields(data=False, m2m=True, **dict(options, export_name_map=True)))
            fields.update((field, (field.name, field.attname)) for field in self.local_many_to_many)

        if data:
            if include_parents:
                for parent in self.parents:
                    # Extend the fields dict with all the m2m fields of each parent.
                    fields.update(parent._meta.get_fields(**dict(options, export_name_map=True)))
            fields.update((field, (field.name, field.attname)) for field in self.local_fields
                          if include_non_concrete or field.column is not None)

        if virtual:
            # Virtual fields to not need to recursively search parents.
            if export_name_map:
                # If we are exporting a map (ex. called by get_field) we do not
                # want to include GenericForeignKeys, but only GenericRelations
                # (Ref. #22994).
                fields.update((field, (field.name, field.attname)) for field in self.virtual_fields
                              if hasattr(field, 'related'))
            else:
                # If we are just listing fields (no map export), we include all
                # virtual fields.
                fields.update((field, (field.name,)) for field in self.virtual_fields)

        if not export_name_map:
            # By default, fields contains field instances as keys and all possible names
            # if the field instance as values. when get_fields is called, we only want to
            # return field instances, so we just preserve the keys.
            fields = tuple(fields.keys())

        # Store result into cache for later access
        self._get_fields_cache[cache_key] = fields
        return fields

    ### CACHED PROPERTIES FOR FAST ACCESS ###

    @cached_property
    def many_to_many(self):
        """
        Returns a list of all many to many fields on the model and
        it's parents.
        All hidden and proxy fields are omitted.
        """
        return list(self.get_fields(data=False, m2m=True))

    @cached_property
    def field_names(self):
        """
        Returns a list of all field names in the model. The list contains
        data, m2m, related objects, related m2m and virtual fields.
        All hidden and proxy fields are omitted.
        """
        res = set()
        for _, names in six.iteritems(self.get_fields(m2m=True, related_objects=True,
                                          related_m2m=True, virtual=True, export_name_map=True)):
            res.update(name for name in names if not name.endswith('+'))
        return list(res)

    @cached_property
    def fields(self):
        """
        Returns a list of all data fields on the model and it's parents.
        All hidden and proxy fields are omitted.
        """
        return list(self.get_fields())

    @cached_property
    def concrete_fields(self):
        """
        Returns a list of all concrete data fields on the model and it's parents.
        All hidden and proxy fields are omitted.
        """
        return list(self.get_fields(include_non_concrete=False))

    @cached_property
    def local_concrete_fields(self):
        """
        Returns a list of all concrete data fields on the model.
        All hidden and proxy fields are omitted.
        """
        return self.get_fields(include_parents=False, include_non_concrete=False)

    ### DEPRECATED METHODS GO BELOW THIS LINE ###

    def get_fields_with_model(self):
        return list(map(self._map_model, self.get_fields()))

    def get_concrete_fields_with_model(self):
        return list(map(self._map_model, self.get_fields(include_non_concrete=False)))

    def get_m2m_with_model(self):
        return list(map(self._map_model, self.get_fields(data=False, m2m=True)))

    def get_field_by_name(self, name):
        return self._map_details(self.get_field(name, m2m=True, related_objects=True,
                                 related_m2m=True, virtual=True))

    def get_all_field_names(self):
        return self.field_names

    def get_all_related_objects(self, local_only=False, include_hidden=False,
                                include_proxy_eq=False):
        include_parents = local_only is False
        return list(self.get_fields(
            data=False, related_objects=True,
            include_parents=include_parents,
            include_hidden=include_hidden,
            include_proxy=include_proxy_eq
        ))

    def get_all_related_objects_with_model(self, local_only=False, include_hidden=False,
                                           include_proxy_eq=False):
        include_parents = local_only is False
        fields = self.get_fields(
            data=False, related_objects=True,
            include_parents=include_parents,
            include_hidden=include_hidden,
            include_proxy=include_proxy_eq
        )
        return list(map(self._map_model, fields))

    def get_all_related_many_to_many_objects(self, local_only=False):
        return list(self.get_fields(data=False, related_m2m=True, include_parents=local_only is not True))

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
        return list(map(self._map_model, self.get_fields(data=False, related_m2m=True)))
