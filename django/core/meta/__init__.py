from django.conf import settings
from django.core import formfields, validators
from django.core import db
from django.core.exceptions import ObjectDoesNotExist
from django.core.meta.fields import *
from django.utils.functional import curry
from django.utils.text import capfirst
import copy, datetime, os, re, sys, types

# Admin stages.
ADD, CHANGE, BOTH = 1, 2, 3

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Prefix (in Python path style) to location of models.
MODEL_PREFIX = 'django.models'

# Methods on models with the following prefix will be removed and
# converted to module-level functions.
MODEL_FUNCTIONS_PREFIX = '_module_'

# Methods on models with the following prefix will be removed and
# converted to manipulator methods.
MANIPULATOR_FUNCTIONS_PREFIX = '_manipulator_'

LOOKUP_SEPARATOR = '__'

####################
# HELPER FUNCTIONS #
####################

# Django currently supports two forms of ordering.
# Form 1 (deprecated) example:
#     order_by=(('pub_date', 'DESC'), ('headline', 'ASC'), (None, 'RANDOM'))
# Form 2 (new-style) example:
#     order_by=('-pub_date', 'headline', '?')
# Form 1 is deprecated and will no longer be supported for Django's first
# official release. The following code converts from Form 1 to Form 2.

LEGACY_ORDERING_MAPPING = {'ASC': '_', 'DESC': '-_', 'RANDOM': '?'}

def handle_legacy_orderlist(order_list):
    if not order_list or isinstance(order_list[0], basestring):
        return order_list
    else:
        import warnings
        new_order_list = [LEGACY_ORDERING_MAPPING[j.upper()].replace('_', str(i)) for i, j in order_list]
        warnings.warn("%r ordering syntax is deprecated. Use %r instead." % (order_list, new_order_list), DeprecationWarning)
        return new_order_list

def orderfield2column(f, opts):
    try:
        return opts.get_field(f, False).column
    except FieldDoesNotExist:
        return f

def orderlist2sql(order_list, opts, prefix=''):
    if prefix.endswith('.'):
        prefix = db.db.quote_name(prefix[:-1]) + '.'
    output = []
    for f in handle_legacy_orderlist(order_list):
        if f.startswith('-'):
            output.append('%s%s DESC' % (prefix, db.db.quote_name(orderfield2column(f[1:], opts))))
        elif f == '?':
            output.append(db.get_random_function_sql())
        else:
            output.append('%s%s ASC' % (prefix, db.db.quote_name(orderfield2column(f, opts))))
    return ', '.join(output)

def get_module(app_label, module_name):
    return __import__('%s.%s.%s' % (MODEL_PREFIX, app_label, module_name), '', '', [''])

def get_app(app_label):
    return __import__('%s.%s' % (MODEL_PREFIX, app_label), '', '', [''])

_installed_models_cache = None
def get_installed_models():
    """
    Returns a list of installed "models" packages, such as foo.models,
    ellington.news.models, etc. This does NOT include django.models.
    """
    global _installed_models_cache
    if _installed_models_cache is not None:
        return _installed_models_cache
    _installed_models_cache = []
    for a in settings.INSTALLED_APPS:
        try:
            _installed_models_cache.append(__import__(a + '.models', '', '', ['']))
        except ImportError:
            pass
    return _installed_models_cache

_installed_modules_cache = None
def get_installed_model_modules(core_models=None):
    """
    Returns a list of installed models, such as django.models.core,
    ellington.news.models.news, foo.models.bar, etc.
    """
    global _installed_modules_cache
    if _installed_modules_cache is not None:
        return _installed_modules_cache
    _installed_modules_cache = []

    # django.models is a special case.
    for submodule in (core_models or []):
        _installed_modules_cache.append(__import__('django.models.%s' % submodule, '', '', ['']))
    for m in get_installed_models():
        for submodule in getattr(m, '__all__', []):
            mod = __import__('django.models.%s' % submodule, '', '', [''])
            try:
                mod._MODELS
            except AttributeError:
                pass # Skip model modules that don't actually have models in them.
            else:
                _installed_modules_cache.append(mod)
    return _installed_modules_cache

class LazyDate:
    """
    Use in limit_choices_to to compare the field to dates calculated at run time
    instead of when the model is loaded.  For example::

        ... limit_choices_to = {'date__gt' : meta.LazyDate(days=-3)} ...

    which will limit the choices to dates greater than three days ago.
    """
    def __init__(self, **kwargs):
        self.delta = datetime.timedelta(**kwargs)

    def __str__(self):
        return str(self.__get_value__())

    def __repr__(self):
        return "<LazyDate: %s>" % self.delta

    def __get_value__(self):
        return datetime.datetime.now() + self.delta

################
# MAIN CLASSES #
################

class FieldDoesNotExist(Exception):
    pass

class BadKeywordArguments(Exception):
    pass

class BoundRelatedObject(object):
    def __init__(self, related_object, field_mapping, original):
        self.relation = related_object
        self.field_mappings = field_mapping[related_object.opts.module_name]

    def template_name(self):
        raise NotImplementedError

    def __repr__(self):
        return repr(self.__dict__)

class RelatedObject(object):
    def __init__(self, parent_opts, opts, field):
        self.parent_opts = parent_opts
        self.opts = opts
        self.field = field
        self.edit_inline = field.rel.edit_inline
        self.name = opts.module_name
        self.var_name = opts.object_name.lower()

    def flatten_data(self, follow, obj=None):
        new_data = {}
        rel_instances = self.get_list(obj)
        for i, rel_instance in enumerate(rel_instances):
            instance_data = {}
            for f in self.opts.fields + self.opts.many_to_many:
                # TODO: Fix for recursive manipulators.
                fol = follow.get(f.name, None)
                if fol:
                    field_data = f.flatten_data(fol, rel_instance)
                    for name, value in field_data.items():
                        instance_data['%s.%d.%s' % (self.var_name, i, name)] = value
            new_data.update(instance_data)
        return new_data

    def extract_data(self, data):
        """
        Pull out the data meant for inline objects of this class,
        i.e. anything starting with our module name.
        """
        return data # TODO

    def get_list(self, parent_instance=None):
        "Get the list of this type of object from an instance of the parent class."
        if parent_instance != None:
            func_name = 'get_%s_list' % self.get_method_name_part()
            func = getattr(parent_instance, func_name)
            list = func()

            count = len(list) + self.field.rel.num_extra_on_change
            if self.field.rel.min_num_in_admin:
               count = max(count, self.field.rel.min_num_in_admin)
            if self.field.rel.max_num_in_admin:
               count = min(count, self.field.rel.max_num_in_admin)

            change = count - len(list)
            if change > 0:
                return list + [None for _ in range(change)]
            if change < 0:
                return list[:change]
            else: # Just right
                return list
        else:
            return [None for _ in range(self.field.rel.num_in_admin)]


    def editable_fields(self):
        "Get the fields in this class that should be edited inline."
        return [f for f in self.opts.fields + self.opts.many_to_many if f.editable and f != self.field]

    def get_follow(self, override=None):
        if isinstance(override, bool):
            if override:
                over = {}
            else:
                return None
        else:
            if override:
                over = override.copy()
            elif self.edit_inline:
                over = {}
            else:
                return None

        over[self.field.name] = False
        return self.opts.get_follow(over)

    def __repr__(self):
        return "<RelatedObject: %s related to %s>" % ( self.name, self.field.name)

    def get_manipulator_fields(self, opts, manipulator, change, follow):
        # TODO: Remove core fields stuff.
        if change:
            meth_name = 'get_%s_count' % self.get_method_name_part()
            count = getattr(manipulator.original_object, meth_name)()
            count += self.field.rel.num_extra_on_change
            if self.field.rel.min_num_in_admin:
                count = max(count, self.field.rel.min_num_in_admin)
            if self.field.rel.max_num_in_admin:
                count = min(count, self.field.rel.max_num_in_admin)
        else:
            count = self.field.rel.num_in_admin

        fields = []
        for i in range(count):
            for f in self.opts.fields + self.opts.many_to_many:
                if follow.get(f.name, False):
                    prefix = '%s.%d.' % (self.var_name, i)
                    fields.extend(f.get_manipulator_fields(self.opts, manipulator, change, name_prefix=prefix, rel=True))
        return fields

    def bind(self, field_mapping, original, bound_related_object_class=BoundRelatedObject):
        return bound_related_object_class(self, field_mapping, original)

    def get_method_name_part(self):
        # This method encapsulates the logic that decides what name to give a
        # method that retrieves related many-to-one or many-to-many objects.
        # Usually it just uses the lower-cased object_name, but if the related
        # object is in another app, the related object's app_label is appended.
        #
        # Examples:
        #
        #   # Normal case -- a related object in the same app.
        #   # This method returns "choice".
        #   Poll.get_choice_list()
        #
        #   # A related object in a different app.
        #   # This method returns "lcom_bestofaward".
        #   Place.get_lcom_bestofaward_list() # "lcom_bestofaward"
        rel_obj_name = self.field.rel.related_name or self.opts.object_name.lower()
        if self.parent_opts.app_label != self.opts.app_label:
            rel_obj_name = '%s_%s' % (self.opts.app_label, rel_obj_name)
        return rel_obj_name

class QBase:
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return '(%s)' % self.operator.join([repr(el) for el in self.args])

    def get_sql(self, opts, table_count):
        tables, join_where, where, params = [], [], [], []
        for val in self.args:
            tables2, join_where2, where2, params2, table_count = val.get_sql(opts, table_count)
            tables.extend(tables2)
            join_where.extend(join_where2)
            where.extend(where2)
            params.extend(params2)
        return tables, join_where, ['(%s)' % self.operator.join(where)], params, table_count

class QAnd(QBase):
    "Encapsulates a combined query that uses 'AND'."
    operator = ' AND '
    def __or__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def __and__(self, other):
        if isinstance(other, QAnd):
            return QAnd(*(self.args+other.args))
        elif isinstance(other, (Q, QOr)):
            return QAnd(*(self.args+(other,)))
        else:
            raise TypeError, other

class QOr(QBase):
    "Encapsulates a combined query that uses 'OR'."
    operator = ' OR '
    def __and__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, QOr):
            return QOr(*(self.args+other.args))
        elif isinstance(other, (Q, QAnd)):
            return QOr(*(self.args+(other,)))
        else:
            raise TypeError, other

class Q:
    "Encapsulates queries for the 'complex' parameter to Django API functions."
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return 'Q%r' % self.kwargs

    def __and__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def get_sql(self, opts, table_count):
        return _parse_lookup(self.kwargs.items(), opts, table_count)

class Options:
    def __init__(self, module_name='', verbose_name='', verbose_name_plural='', db_table='',
        fields=None, ordering=None, unique_together=None, admin=None, has_related_links=False,
        where_constraints=None, object_name=None, app_label=None,
        exceptions=None, permissions=None, get_latest_by=None,
        order_with_respect_to=None, module_constants=None):

        # Save the original function args, for use by copy(). Note that we're
        # NOT using copy.deepcopy(), because that would create a new copy of
        # everything in memory, and it's better to conserve memory. Of course,
        # this comes with the important gotcha that changing any attribute of
        # this object will change its value in self._orig_init_args, so we
        # need to be careful not to do that. In practice, we can pull this off
        # because Options are generally read-only objects, and __init__() is
        # the only place where its attributes are manipulated.

        # locals() is used purely for convenience, so we don't have to do
        # something verbose like this:
        #    self._orig_init_args = {
        #       'module_name': module_name,
        #       'verbose_name': verbose_name,
        #       ...
        #    }
        self._orig_init_args = locals()
        del self._orig_init_args['self'] # because we don't care about it.

        # Move many-to-many related fields from self.fields into self.many_to_many.
        self.fields, self.many_to_many = [], []
        for field in (fields or []):
            if field.rel and isinstance(field.rel, ManyToMany):
                self.many_to_many.append(field)
            else:
                self.fields.append(field)
        self.module_name, self.verbose_name = module_name, verbose_name
        self.verbose_name_plural = verbose_name_plural or verbose_name + 's'
        self.db_table, self.has_related_links = db_table, has_related_links
        self.ordering = ordering or []
        self.unique_together = unique_together or []
        self.where_constraints = where_constraints or []
        self.exceptions = exceptions or []
        self.permissions = permissions or []
        self.object_name, self.app_label = object_name, app_label
        self.get_latest_by = get_latest_by
        if order_with_respect_to:
            self.order_with_respect_to = self.get_field(order_with_respect_to)
            self.ordering = ('_order',)
        else:
            self.order_with_respect_to = None
        self.module_constants = module_constants or {}
        self.admin = admin

        # Calculate one_to_one_field.
        self.one_to_one_field = None
        for f in self.fields:
            if isinstance(f.rel, OneToOne):
                self.one_to_one_field = f
                break
        # Cache the primary-key field.
        self.pk = None
        for f in self.fields:
            if f.primary_key:
                self.pk = f
                break
        # If a primary_key field hasn't been specified, add an
        # auto-incrementing primary-key ID field automatically.
        if self.pk is None:
            self.fields.insert(0, AutoField(name='id', verbose_name='ID', primary_key=True))
            self.pk = self.fields[0]
        # Cache whether this has an AutoField.
        self.has_auto_field = False
        for f in self.fields:
            is_auto = isinstance(f, AutoField)
            if is_auto and self.has_auto_field:
                raise AssertionError, "A model can't have more than one AutoField."
            elif is_auto:
                self.has_auto_field = True

    def __repr__(self):
        return '<Options for %s>' % self.module_name

    def copy(self, **kwargs):
        args = self._orig_init_args.copy()
        args.update(kwargs)
        return self.__class__(**args)

    def get_model_module(self):
        return get_module(self.app_label, self.module_name)

    def get_content_type_id(self):
        "Returns the content-type ID for this object type."
        if not hasattr(self, '_content_type_id'):
            mod = get_module('core', 'contenttypes')
            self._content_type_id = mod.get_object(python_module_name__exact=self.module_name, package__label__exact=self.app_label).id
        return self._content_type_id

    def get_field(self, name, many_to_many=True):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        to_search = many_to_many and (self.fields + self.many_to_many) or self.fields
        for f in to_search:
            if f.name == name:
                return f
        raise FieldDoesNotExist, "name=%s" % name

    def get_order_sql(self, table_prefix=''):
        "Returns the full 'ORDER BY' clause for this object, according to self.ordering."
        if not self.ordering: return ''
        pre = table_prefix and (table_prefix + '.') or ''
        return 'ORDER BY ' + orderlist2sql(self.ordering, self, pre)

    def get_add_permission(self):
        return 'add_%s' % self.object_name.lower()

    def get_change_permission(self):
        return 'change_%s' % self.object_name.lower()

    def get_delete_permission(self):
        return 'delete_%s' % self.object_name.lower()

    def get_all_related_objects(self):
        try: # Try the cache first.
            return self._all_related_objects
        except AttributeError:
            module_list = get_installed_model_modules()
            rel_objs = []
            for mod in module_list:
                for klass in mod._MODELS:
                    for f in klass._meta.fields:
                        if f.rel and self == f.rel.to:
                            rel_objs.append(RelatedObject(self, klass._meta, f))
            if self.has_related_links:
                # Manually add RelatedLink objects, which are a special case.
                relatedlinks = get_module('relatedlinks', 'relatedlinks')
                # Note that the copy() is very important -- otherwise any
                # subsequently loaded object with related links will override this
                # relationship we're adding.
                link_field = copy.copy(relatedlinks.RelatedLink._meta.get_field('object_id'))
                link_field.rel = ManyToOne(self.get_model_module().Klass, 'id',
                    num_in_admin=3, min_num_in_admin=3, edit_inline=TABULAR,
                    lookup_overrides={
                        'content_type__package__label__exact': self.app_label,
                        'content_type__python_module_name__exact': self.module_name,
                    })
                rel_objs.append(RelatedObject(self, relatedlinks.RelatedLink._meta, link_field))
            self._all_related_objects = rel_objs
            return rel_objs

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
            if override and override.has_key(f.name):
                child_override = override[f.name]
            else:
                child_override = None
            fol = f.get_follow(child_override)
            if fol:
                follow[f.name] = fol
        return follow

    def get_all_related_many_to_many_objects(self):
        module_list = get_installed_model_modules()
        rel_objs = []
        for mod in module_list:
            for klass in mod._MODELS:
                for f in klass._meta.many_to_many:
                    if f.rel and self == f.rel.to:
                        rel_objs.append(RelatedObject(self, klass._meta, f))
        return rel_objs

    def get_ordered_objects(self):
        "Returns a list of Options objects that are ordered with respect to this object."
        if not hasattr(self, '_ordered_objects'):
            objects = []
            for klass in get_app(self.app_label)._MODELS:
                opts = klass._meta
                if opts.order_with_respect_to and opts.order_with_respect_to.rel \
                    and self == opts.order_with_respect_to.rel.to:
                    objects.append(opts)
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
        if not self._field_types.has_key(field_type):
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

def _reassign_globals(function_dict, extra_globals, namespace):
    new_functions = {}
    for k, v in function_dict.items():
        # Get the code object.
        code = v.func_code
        # Recreate the function, but give it access to extra_globals and the
        # given namespace's globals, too.
        new_globals = {'__builtins__': __builtins__, 'db': db.db, 'datetime': datetime}
        new_globals.update(extra_globals.__dict__)
        func = types.FunctionType(code, globals=new_globals, name=k, argdefs=v.func_defaults)
        func.__dict__.update(v.__dict__)
        setattr(namespace, k, func)
        # For all of the custom functions that have been added so far, give
        # them access to the new function we've just created.
        for new_k, new_v in new_functions.items():
            new_v.func_globals[k] = func
        new_functions[k] = func

# Calculate the module_name using a poor-man's pluralization.
get_module_name = lambda class_name: class_name.lower() + 's'

# Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
get_verbose_name = lambda class_name: re.sub('([A-Z])', ' \\1', class_name).lower().strip()

class ModelBase(type):
    "Metaclass for all models"
    def __new__(cls, name, bases, attrs):
        # If this isn't a subclass of Model, don't do anything special.
        if not bases:
            return type.__new__(cls, name, bases, attrs)

        try:
            meta_attrs = attrs.pop('META').__dict__
            del meta_attrs['__module__']
            del meta_attrs['__doc__']
        except KeyError:
            meta_attrs = {}

        # Gather all attributes that are Field instances.
        fields = []
        for obj_name, obj in attrs.items():
            if isinstance(obj, Field):
                obj.set_name(obj_name)
                fields.append(obj)
                del attrs[obj_name]

        # Sort the fields in the order that they were created. The
        # "creation_counter" is needed because metaclasses don't preserve the
        # attribute order.
        fields.sort(lambda x, y: x.creation_counter - y.creation_counter)

        # If this model is a subclass of another model, create an Options
        # object by first copying the base class's _meta and then updating it
        # with the overrides from this class.
        replaces_module = None
        if bases[0] != Model:
            field_names = [f.name for f in fields]
            remove_fields = meta_attrs.pop('remove_fields', [])
            for f in bases[0]._meta._orig_init_args['fields']:
                if f.name not in field_names and f.name not in remove_fields:
                    fields.insert(0, f)
            if meta_attrs.has_key('replaces_module'):
                # Set the replaces_module variable for now. We can't actually
                # do anything with it yet, because the module hasn't yet been
                # created.
                replaces_module = meta_attrs.pop('replaces_module').split('.')
            # Pass any Options overrides to the base's Options instance, and
            # simultaneously remove them from attrs. When this is done, attrs
            # will be a dictionary of custom methods, plus __module__.
            meta_overrides = {'fields': fields, 'module_name': get_module_name(name), 'verbose_name': get_verbose_name(name)}
            for k, v in meta_attrs.items():
                if not callable(v) and k != '__module__':
                    meta_overrides[k] = meta_attrs.pop(k)
            opts = bases[0]._meta.copy(**meta_overrides)
            opts.object_name = name
            del meta_overrides
        else:
            opts = Options(
                module_name = meta_attrs.pop('module_name', get_module_name(name)),
                # If the verbose_name wasn't given, use the class name,
                # converted from InitialCaps to "lowercase with spaces".
                verbose_name = meta_attrs.pop('verbose_name', get_verbose_name(name)),
                verbose_name_plural = meta_attrs.pop('verbose_name_plural', ''),
                db_table = meta_attrs.pop('db_table', ''),
                fields = fields,
                ordering = meta_attrs.pop('ordering', None),
                unique_together = meta_attrs.pop('unique_together', None),
                admin = meta_attrs.pop('admin', None),
                has_related_links = meta_attrs.pop('has_related_links', False),
                where_constraints = meta_attrs.pop('where_constraints', None),
                object_name = name,
                app_label = meta_attrs.pop('app_label', None),
                exceptions = meta_attrs.pop('exceptions', None),
                permissions = meta_attrs.pop('permissions', None),
                get_latest_by = meta_attrs.pop('get_latest_by', None),
                order_with_respect_to = meta_attrs.pop('order_with_respect_to', None),
                module_constants = meta_attrs.pop('module_constants', None),
            )

        if meta_attrs != {}:
            raise TypeError, "'class META' got invalid attribute(s): %s" % ','.join(meta_attrs.keys())

        # Dynamically create the module that will contain this class and its
        # associated helper functions.
        if replaces_module is not None:
            new_mod = get_module(*replaces_module)
        else:
            new_mod = types.ModuleType(opts.module_name)

        # Collect any/all custom class methods and module functions, and move
        # them to a temporary holding variable. We'll deal with them later.
        if replaces_module is not None:
            # Initialize these values to the base class' custom_methods and
            # custom_functions.
            custom_methods = dict([(k, v) for k, v in new_mod.Klass.__dict__.items() if hasattr(v, 'custom')])
            custom_functions = dict([(k, v) for k, v in new_mod.__dict__.items() if hasattr(v, 'custom')])
        else:
            custom_methods, custom_functions = {}, {}
        manipulator_methods = {}
        for k, v in attrs.items():
            if k in ('__module__', '__init__', '_overrides', '__doc__'):
                continue # Skip the important stuff.
            assert callable(v), "%r is an invalid model parameter." % k
            # Give the function a function attribute "custom" to designate that
            # it's a custom function/method.
            v.custom = True
            if k.startswith(MODEL_FUNCTIONS_PREFIX):
                custom_functions[k[len(MODEL_FUNCTIONS_PREFIX):]] = v
            elif k.startswith(MANIPULATOR_FUNCTIONS_PREFIX):
                manipulator_methods[k[len(MANIPULATOR_FUNCTIONS_PREFIX):]] = v
            else:
                custom_methods[k] = v
            del attrs[k]

        # Create the module-level ObjectDoesNotExist exception.
        dne_exc_name = '%sDoesNotExist' % name
        does_not_exist_exception = types.ClassType(dne_exc_name, (ObjectDoesNotExist,), {})
        # Explicitly set its __module__ because it will initially (incorrectly)
        # be set to the module the code is being executed in.
        does_not_exist_exception.__module__ = MODEL_PREFIX + '.' + opts.module_name
        setattr(new_mod, dne_exc_name, does_not_exist_exception)

        # Create other exceptions.
        for exception_name in opts.exceptions:
            exc = types.ClassType(exception_name, (Exception,), {})
            exc.__module__ = MODEL_PREFIX + '.' + opts.module_name # Set this explicitly, as above.
            setattr(new_mod, exception_name, exc)

        # Create any module-level constants, if applicable.
        for k, v in opts.module_constants.items():
            setattr(new_mod, k, v)

        # Create the default class methods.
        attrs['__init__'] = curry(method_init, opts)
        attrs['__eq__'] = curry(method_eq, opts)
        attrs['__ne__'] = curry(method_ne, opts)
        attrs['save'] = curry(method_save, opts)
        attrs['save'].alters_data = True
        attrs['delete'] = curry(method_delete, opts)
        attrs['delete'].alters_data = True

        if opts.order_with_respect_to:
            attrs['get_next_in_order'] = curry(method_get_next_in_order, opts, opts.order_with_respect_to)
            attrs['get_previous_in_order'] = curry(method_get_previous_in_order, opts, opts.order_with_respect_to)

        for f in opts.fields:
            # If the object has a relationship to itself, as designated by
            # RECURSIVE_RELATIONSHIP_CONSTANT, create that relationship formally.
            if f.rel and f.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT:
                f.rel.to = opts
                f.name = f.name or (f.rel.to.object_name.lower() + '_' + f.rel.to.pk.name)
                f.verbose_name = f.verbose_name or f.rel.to.verbose_name
                f.rel.field_name = f.rel.field_name or f.rel.to.pk.name
            # Add "get_thingie" methods for many-to-one related objects.
            # EXAMPLES: Choice.get_poll(), Story.get_dateline()
            if isinstance(f.rel, ManyToOne):
                func = curry(method_get_many_to_one, f)
                func.__doc__ = "Returns the associated `%s.%s` object." % (f.rel.to.app_label, f.rel.to.module_name)
                attrs['get_%s' % f.name] = func

        for f in opts.many_to_many:
            # Add "get_thingie" methods for many-to-many related objects.
            # EXAMPLES: Poll.get_site_list(), Story.get_byline_list()
            func = curry(method_get_many_to_many, f)
            func.__doc__ = "Returns a list of associated `%s.%s` objects." % (f.rel.to.app_label, f.rel.to.module_name)
            attrs['get_%s_list' % f.rel.singular] = func
            # Add "set_thingie" methods for many-to-many related objects.
            # EXAMPLES: Poll.set_sites(), Story.set_bylines()
            func = curry(method_set_many_to_many, f)
            func.__doc__ = "Resets this object's `%s.%s` list to the given list of IDs. Note that it doesn't check whether the given IDs are valid." % (f.rel.to.app_label, f.rel.to.module_name)
            func.alters_data = True
            attrs['set_%s' % f.name] = func

        # Create the class, because we need it to use in currying.
        new_class = type.__new__(cls, name, bases, attrs)

        # Give the class a docstring -- its definition.
        if new_class.__doc__ is None:
            new_class.__doc__ = "%s.%s(%s)" % (opts.module_name, name, ", ".join([f.name for f in opts.fields]))

        # Create the standard, module-level API helper functions such
        # as get_object() and get_list().
        new_mod.get_object = curry(function_get_object, opts, new_class, does_not_exist_exception)
        new_mod.get_object.__doc__ = "Returns the %s object matching the given parameters." % name

        new_mod.get_list = curry(function_get_list, opts, new_class)
        new_mod.get_list.__doc__ = "Returns a list of %s objects matching the given parameters." % name

        new_mod.get_iterator = curry(function_get_iterator, opts, new_class)
        new_mod.get_iterator.__doc__ = "Returns an iterator of %s objects matching the given parameters." % name

        new_mod.get_values = curry(function_get_values, opts, new_class)
        new_mod.get_values.__doc__ = "Returns a list of dictionaries matching the given parameters."

        new_mod.get_values_iterator = curry(function_get_values_iterator, opts, new_class)
        new_mod.get_values_iterator.__doc__ = "Returns an iterator of dictionaries matching the given parameters."

        new_mod.get_count = curry(function_get_count, opts)
        new_mod.get_count.__doc__ = "Returns the number of %s objects matching the given parameters." % name

        new_mod._get_sql_clause = curry(function_get_sql_clause, opts)

        new_mod.get_in_bulk = curry(function_get_in_bulk, opts, new_class)
        new_mod.get_in_bulk.__doc__ = "Returns a dictionary of ID -> %s for the %s objects with IDs in the given id_list." % (name, name)

        if opts.get_latest_by:
            new_mod.get_latest = curry(function_get_latest, opts, new_class, does_not_exist_exception)

        for f in opts.fields:
            #TODO : change this into a virtual function so that user defined fields will be able to add methods to module or class.
            if f.choices:
                # Add "get_thingie_display" method to get human-readable value.
                func = curry(method_get_display_value, f)
                setattr(new_class, 'get_%s_display' % f.name, func)
            if isinstance(f, DateField) or isinstance(f, DateTimeField):
                # Add "get_next_by_thingie" and "get_previous_by_thingie" methods
                # for all DateFields and DateTimeFields that cannot be null.
                # EXAMPLES: Poll.get_next_by_pub_date(), Poll.get_previous_by_pub_date()
                if not f.null:
                    setattr(new_class, 'get_next_by_%s' % f.name, curry(method_get_next_or_previous, new_mod.get_object, opts, f, True))
                    setattr(new_class, 'get_previous_by_%s' % f.name, curry(method_get_next_or_previous, new_mod.get_object, opts, f, False))
                # Add "get_thingie_list" for all DateFields and DateTimeFields.
                # EXAMPLE: polls.get_pub_date_list()
                func = curry(function_get_date_list, opts, f)
                func.__doc__ = "Returns a list of days, months or years (as datetime.datetime objects) in which %s objects are available. The first parameter ('kind') must be one of 'year', 'month' or 'day'." % name
                setattr(new_mod, 'get_%s_list' % f.name, func)

            elif isinstance(f, FileField):
                setattr(new_class, 'get_%s_filename' % f.name, curry(method_get_file_filename, f))
                setattr(new_class, 'get_%s_url' % f.name, curry(method_get_file_url, f))
                setattr(new_class, 'get_%s_size' % f.name, curry(method_get_file_size, f))
                func = curry(method_save_file, f)
                func.alters_data = True
                setattr(new_class, 'save_%s_file' % f.name, func)
                if isinstance(f, ImageField):
                    # Add get_BLAH_width and get_BLAH_height methods, but only
                    # if the image field doesn't have width and height cache
                    # fields.
                    if not f.width_field:
                        setattr(new_class, 'get_%s_width' % f.name, curry(method_get_image_width, f))
                    if not f.height_field:
                        setattr(new_class, 'get_%s_height' % f.name, curry(method_get_image_height, f))

        # Add the class itself to the new module we've created.
        new_mod.__dict__[name] = new_class

        # Add "Klass" -- a shortcut reference to the class.
        new_mod.__dict__['Klass'] = new_class

        # Add the Manipulators.
        new_mod.__dict__['AddManipulator'] = get_manipulator(opts, new_class, manipulator_methods, add=True)
        new_mod.__dict__['ChangeManipulator'] = get_manipulator(opts, new_class, manipulator_methods, change=True)

        # Now that we have references to new_mod and new_class, we can add
        # any/all extra class methods to the new class. Note that we could
        # have just left the extra methods in attrs (above), but that would
        # have meant that any code within the extra methods would *not* have
        # access to module-level globals, such as get_list(), db, etc.
        # In order to give these methods access to those globals, we have to
        # deconstruct the method getting its raw "code" object, then recreating
        # the function with a new "globals" dictionary.
        #
        # To complicate matters more, because each method is manually assigned
        # a "globals" value, that "globals" value does NOT include the methods
        # that haven't been created yet. For instance, if there are two custom
        # methods, foo() and bar(), and foo() is created first, it won't have
        # bar() within its globals(). This is a problem because sometimes
        # custom methods/functions refer to other custom methods/functions. To
        # solve this problem, we keep track of the new functions created (in
        # the new_functions variable) and manually append each new function to
        # the func_globals() of all previously-created functions. So, by the
        # end of the loop, all functions will "know" about all the other
        # functions.
        _reassign_globals(custom_methods, new_mod, new_class)
        _reassign_globals(custom_functions, new_mod, new_mod)
        _reassign_globals(manipulator_methods, new_mod, new_mod.__dict__['AddManipulator'])
        _reassign_globals(manipulator_methods, new_mod, new_mod.__dict__['ChangeManipulator'])

        if hasattr(new_class, 'get_absolute_url'):
            new_class.get_absolute_url = curry(get_absolute_url, opts, new_class.get_absolute_url)

        # Get a reference to the module the class is in, and dynamically add
        # the new module to it.
        app_package = sys.modules.get(new_class.__module__)
        if replaces_module is not None:
            app_label = replaces_module[0]
        else:
            app_package.__dict__[opts.module_name] = new_mod
            app_label = app_package.__name__[app_package.__name__.rfind('.')+1:]

            # Populate the _MODELS member on the module the class is in.
            # Example: django.models.polls will have a _MODELS member that will
            # contain this list:
            # [<class 'django.models.polls.Poll'>, <class 'django.models.polls.Choice'>]
            # Don't do this if replaces_module is set.
            app_package.__dict__.setdefault('_MODELS', []).append(new_class)

        # Cache the app label.
        opts.app_label = app_label

        # If the db_table wasn't provided, use the app_label + module_name.
        if not opts.db_table:
            opts.db_table = "%s_%s" % (app_label, opts.module_name)
        new_class._meta = opts

        # Set the __file__ attribute to the __file__ attribute of its package,
        # because they're technically from the same file. Note: if we didn't
        # set this, sys.modules would think this module was built-in.
        try:
            new_mod.__file__ = app_package.__file__
        except AttributeError:
            # 'module' object has no attribute '__file__', which means the
            # class was probably being entered via the interactive interpreter.
            pass

        # Add the module's entry to sys.modules -- for instance,
        # "django.models.polls.polls". Note that "django.models.polls" has already
        # been added automatically.
        sys.modules.setdefault('%s.%s.%s' % (MODEL_PREFIX, app_label, opts.module_name), new_mod)

        # If this module replaces another one, get a reference to the other
        # module's parent, and replace the other module with the one we've just
        # created.
        if replaces_module is not None:
            old_app = get_app(replaces_module[0])
            setattr(old_app, replaces_module[1], new_mod)
            for i, model in enumerate(old_app._MODELS):
                if model._meta.module_name == replaces_module[1]:
                    # Replace the appropriate member of the old app's _MODELS
                    # data structure.
                    old_app._MODELS[i] = new_class
                    # Replace all relationships to the old class with
                    # relationships to the new one.
                    for related in model._meta.get_all_related_objects() + model._meta.get_all_related_many_to_many_objects():
                        related.field.rel.to = opts
                    break
        return new_class

class Model:
    __metaclass__ = ModelBase

    def __repr__(self):
        return '<%s object>' % self.__class__.__name__

############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# CORE METHODS #############################

def method_init(opts, self, *args, **kwargs):
    if kwargs:
        for f in opts.fields:
            if isinstance(f.rel, ManyToOne):
                try:
                    # Assume object instance was passed in.
                    rel_obj = kwargs.pop(f.name)
                except KeyError:
                    try:
                        # Object instance wasn't passed in -- must be an ID.
                        val = kwargs.pop(f.attname)
                    except KeyError:
                        val = f.get_default()
                else:
                    # Object instance was passed in.
                    # Special case: You can pass in "None" for related objects if it's allowed.
                    if rel_obj is None and f.null:
                        val = None
                    else:
                        try:
                            val = getattr(rel_obj, f.rel.get_related_field().attname)
                        except AttributeError:
                            raise TypeError, "Invalid value: %r should be a %s instance, not a %s" % (f.name, f.rel.to, type(rel_obj))
                setattr(self, f.attname, val)
            else:
                val = kwargs.pop(f.attname, f.get_default())
                setattr(self, f.attname, val)
        if kwargs:
            raise TypeError, "'%s' is an invalid keyword argument for this function" % kwargs.keys()[0]
    for i, arg in enumerate(args):
        setattr(self, opts.fields[i].attname, arg)

def method_eq(opts, self, other):
    return isinstance(other, self.__class__) and getattr(self, opts.pk.attname) == getattr(other, opts.pk.attname)

def method_ne(opts, self, other):
    return not method_eq(opts, self, other)

def method_save(opts, self):
    # Run any pre-save hooks.
    if hasattr(self, '_pre_save'):
        self._pre_save()
    non_pks = [f for f in opts.fields if not f.primary_key]
    cursor = db.db.cursor()

    # First, try an UPDATE. If that doesn't update anything, do an INSERT.
    pk_val = getattr(self, opts.pk.attname)
    pk_set = bool(pk_val)
    record_exists = True
    if pk_set:
        # Determine whether a record with the primary key already exists.
        cursor.execute("SELECT 1 FROM %s WHERE %s=%%s LIMIT 1" % \
            (db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column)), [pk_val])
        # If it does already exist, do an UPDATE.
        if cursor.fetchone():
            db_values = [f.get_db_prep_save(f.pre_save(getattr(self, f.attname), False)) for f in non_pks]
            cursor.execute("UPDATE %s SET %s WHERE %s=%%s" % \
                (db.db.quote_name(opts.db_table),
                ','.join(['%s=%%s' % db.db.quote_name(f.column) for f in non_pks]),
                db.db.quote_name(opts.pk.attname)),
                db_values + [pk_val])
        else:
            record_exists = False
    if not pk_set or not record_exists:
        field_names = [db.db.quote_name(f.column) for f in opts.fields if not isinstance(f, AutoField)]
        db_values = [f.get_db_prep_save(f.pre_save(getattr(self, f.attname), True)) for f in opts.fields if not isinstance(f, AutoField)]
        # If the PK has been manually set we must respect that
        if pk_set:
            field_names += [f.column for f in opts.fields if isinstance(f, AutoField)]
            db_values += [f.get_db_prep_save(f.pre_save(getattr(self, f.column), True)) for f in opts.fields if isinstance(f, AutoField)]
        placeholders = ['%s'] * len(field_names)
        if opts.order_with_respect_to:
            field_names.append(db.db.quote_name('_order'))
            # TODO: This assumes the database supports subqueries.
            placeholders.append('(SELECT COUNT(*) FROM %s WHERE %s = %%s)' % \
                (db.db.quote_name(opts.db_table), db.db.quote_name(opts.order_with_respect_to.column)))
            db_values.append(getattr(self, opts.order_with_respect_to.attname))
        cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
            (db.db.quote_name(opts.db_table), ','.join(field_names),
            ','.join(placeholders)), db_values)
        if opts.has_auto_field and not pk_set:
            setattr(self, opts.pk.attname, db.get_last_insert_id(cursor, opts.db_table, opts.pk.column))
    db.db.commit()
    # Run any post-save hooks.
    if hasattr(self, '_post_save'):
        self._post_save()

def method_delete(opts, self):
    assert getattr(self, opts.pk.attname) is not None, "%r can't be deleted because it doesn't have an ID."
    # Run any pre-delete hooks.
    if hasattr(self, '_pre_delete'):
        self._pre_delete()
    cursor = db.db.cursor()
    for related in opts.get_all_related_objects():
        rel_opts_name = related.get_method_name_part()
        if isinstance(related.field.rel, OneToOne):
            try:
                sub_obj = getattr(self, 'get_%s' % rel_opts_name)()
            except ObjectDoesNotExist:
                pass
            else:
                sub_obj.delete()
        else:
            for sub_obj in getattr(self, 'get_%s_list' % rel_opts_name)():
                sub_obj.delete()
    for related in opts.get_all_related_many_to_many_objects():
        cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
            (db.db.quote_name(related.field.get_m2m_db_table(related.opts)),
            db.db.quote_name(self._meta.object_name.lower() + '_id')), [getattr(self, opts.pk.attname)])
    for f in opts.many_to_many:
        cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
            (db.db.quote_name(f.get_m2m_db_table(opts)),
            db.db.quote_name(self._meta.object_name.lower() + '_id')),
            [getattr(self, opts.pk.attname)])
    cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
        (db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column)),
        [getattr(self, opts.pk.attname)])
    db.db.commit()
    setattr(self, opts.pk.attname, None)
    for f in opts.fields:
        if isinstance(f, FileField) and getattr(self, f.attname):
            file_name = getattr(self, 'get_%s_filename' % f.name)()
            # If the file exists and no other object of this type references it,
            # delete it from the filesystem.
            if os.path.exists(file_name) and not opts.get_model_module().get_list(**{'%s__exact' % f.name: getattr(self, f.name)}):
                os.remove(file_name)
    # Run any post-delete hooks.
    if hasattr(self, '_post_delete'):
        self._post_delete()

def method_get_next_in_order(opts, order_field, self):
    if not hasattr(self, '_next_in_order_cache'):
        self._next_in_order_cache = opts.get_model_module().get_object(order_by=('_order',),
            where=['%s > (SELECT %s FROM %s WHERE %s=%%s)' % \
                (db.db.quote_name('_order'), db.db.quote_name('_order'),
                db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column)),
                '%s=%%s' % db.db.quote_name(order_field.column)], limit=1,
            params=[getattr(self, opts.pk.attname), getattr(self, order_field.attname)])
    return self._next_in_order_cache

def method_get_previous_in_order(opts, order_field, self):
    if not hasattr(self, '_previous_in_order_cache'):
        self._previous_in_order_cache = opts.get_model_module().get_object(order_by=('-_order',),
            where=['%s < (SELECT %s FROM %s WHERE %s=%%s)' % \
                (db.db.quote_name('_order'), db.db.quote_name('_order'),
                db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column)),
                '%s=%%s' % db.db.quote_name(order_field.column)], limit=1,
            params=[getattr(self, opts.pk.attname), getattr(self, order_field.attname)])
    return self._previous_in_order_cache

# RELATIONSHIP METHODS #####################

# Example: Story.get_dateline()
def method_get_many_to_one(field_with_rel, self):
    cache_var = field_with_rel.get_cache_name()
    if not hasattr(self, cache_var):
        val = getattr(self, field_with_rel.attname)
        mod = field_with_rel.rel.to.get_model_module()
        if val is None:
            raise getattr(mod, '%sDoesNotExist' % field_with_rel.rel.to.object_name)
        other_field = field_with_rel.rel.get_related_field()
        if other_field.rel:
            params = {'%s__%s__exact' % (field_with_rel.rel.field_name, other_field.rel.field_name): val}
        else:
            params = {'%s__exact'% field_with_rel.rel.field_name: val}
        retrieved_obj = mod.get_object(**params)
        setattr(self, cache_var, retrieved_obj)
    return getattr(self, cache_var)

# Handles getting many-to-many related objects.
# Example: Poll.get_site_list()
def method_get_many_to_many(field_with_rel, self):
    rel = field_with_rel.rel.to
    cache_var = '_%s_cache' % field_with_rel.name
    if not hasattr(self, cache_var):
        mod = rel.get_model_module()
        sql = "SELECT %s FROM %s a, %s b WHERE a.%s = b.%s AND b.%s = %%s %s" % \
            (','.join(['a.%s' % db.db.quote_name(f.column) for f in rel.fields]),
            db.db.quote_name(rel.db_table),
            db.db.quote_name(field_with_rel.get_m2m_db_table(self._meta)),
            db.db.quote_name(rel.pk.column),
            db.db.quote_name(rel.object_name.lower() + '_id'),
            db.db.quote_name(self._meta.object_name.lower() + '_id'), rel.get_order_sql('a'))
        cursor = db.db.cursor()
        cursor.execute(sql, [getattr(self, self._meta.pk.attname)])
        setattr(self, cache_var, [getattr(mod, rel.object_name)(*row) for row in cursor.fetchall()])
    return getattr(self, cache_var)

# Handles setting many-to-many relationships.
# Example: Poll.set_sites()
def method_set_many_to_many(rel_field, self, id_list):
    current_ids = [obj.id for obj in method_get_many_to_many(rel_field, self)]
    ids_to_add, ids_to_delete = dict([(i, 1) for i in id_list]), []
    for current_id in current_ids:
        if current_id in id_list:
            del ids_to_add[current_id]
        else:
            ids_to_delete.append(current_id)
    ids_to_add = ids_to_add.keys()
    # Now ids_to_add is a list of IDs to add, and ids_to_delete is a list of IDs to delete.
    if not ids_to_delete and not ids_to_add:
        return False # No change
    rel = rel_field.rel.to
    m2m_table = rel_field.get_m2m_db_table(self._meta)
    cursor = db.db.cursor()
    this_id = getattr(self, self._meta.pk.attname)
    if ids_to_delete:
        sql = "DELETE FROM %s WHERE %s = %%s AND %s IN (%s)" % \
            (db.db.quote_name(m2m_table),
            db.db.quote_name(self._meta.object_name.lower() + '_id'),
            db.db.quote_name(rel.object_name.lower() + '_id'), ','.join(map(str, ids_to_delete)))
        cursor.execute(sql, [this_id])
    if ids_to_add:
        sql = "INSERT INTO %s (%s, %s) VALUES (%%s, %%s)" % \
            (db.db.quote_name(m2m_table),
            db.db.quote_name(self._meta.object_name.lower() + '_id'),
            db.db.quote_name(rel.object_name.lower() + '_id'))
        cursor.executemany(sql, [(this_id, i) for i in ids_to_add])
    db.db.commit()
    try:
        delattr(self, '_%s_cache' % rel_field.name) # clear cache, if it exists
    except AttributeError:
        pass
    return True

# Handles related-object retrieval.
# Examples: Poll.get_choice(), Poll.get_choice_list(), Poll.get_choice_count()
def method_get_related(method_name, rel_mod, rel_field, self, **kwargs):
    if self._meta.has_related_links and rel_mod.Klass._meta.module_name == 'relatedlinks':
        kwargs['object_id__exact'] = getattr(self, rel_field.rel.field_name)
    else:
        kwargs['%s__%s__exact' % (rel_field.name, rel_field.rel.to.pk.name)] = getattr(self, rel_field.rel.get_related_field().attname)
    kwargs.update(rel_field.rel.lookup_overrides)
    return getattr(rel_mod, method_name)(**kwargs)

# Handles adding related objects.
# Example: Poll.add_choice()
def method_add_related(rel_obj, rel_mod, rel_field, self, *args, **kwargs):
    init_kwargs = dict(zip([f.attname for f in rel_obj.fields if f != rel_field and not isinstance(f, AutoField)], args))
    init_kwargs.update(kwargs)
    for f in rel_obj.fields:
        if isinstance(f, AutoField):
            init_kwargs[f.attname] = None
    init_kwargs[rel_field.name] = self
    obj = rel_mod.Klass(**init_kwargs)
    obj.save()
    return obj

# Handles related many-to-many object retrieval.
# Examples: Album.get_song(), Album.get_song_list(), Album.get_song_count()
def method_get_related_many_to_many(method_name, opts, rel_mod, rel_field, self, **kwargs):
    kwargs['%s__%s__exact' % (rel_field.name, opts.pk.name)] = getattr(self, opts.pk.attname)
    return getattr(rel_mod, method_name)(**kwargs)

# Handles setting many-to-many related objects.
# Example: Album.set_songs()
def method_set_related_many_to_many(rel_opts, rel_field, self, id_list):
    id_list = map(int, id_list) # normalize to integers
    rel = rel_field.rel.to
    m2m_table = rel_field.get_m2m_db_table(rel_opts)
    this_id = getattr(self, self._meta.pk.attname)
    cursor = db.db.cursor()
    cursor.execute("DELETE FROM %s WHERE %s = %%s" % \
        (db.db.quote_name(m2m_table),
        db.db.quote_name(rel.object_name.lower() + '_id')), [this_id])
    sql = "INSERT INTO %s (%s, %s) VALUES (%%s, %%s)" % \
        (db.db.quote_name(m2m_table),
        db.db.quote_name(rel.object_name.lower() + '_id'),
        db.db.quote_name(rel_opts.object_name.lower() + '_id'))
    cursor.executemany(sql, [(this_id, i) for i in id_list])
    db.db.commit()

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list):
    cursor = db.db.cursor()
    # Example: "UPDATE poll_choices SET _order = %s WHERE poll_id = %s AND id = %s"
    sql = "UPDATE %s SET %s = %%s WHERE %s = %%s AND %s = %%s" % \
        (db.db.quote_name(ordered_obj.db_table), db.db.quote_name('_order'),
        db.db.quote_name(ordered_obj.order_with_respect_to.column),
        db.db.quote_name(ordered_obj.pk.column))
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.executemany(sql, [(i, rel_val, j) for i, j in enumerate(id_list)])
    db.db.commit()

def method_get_order(ordered_obj, self):
    cursor = db.db.cursor()
    # Example: "SELECT id FROM poll_choices WHERE poll_id = %s ORDER BY _order"
    sql = "SELECT %s FROM %s WHERE %s = %%s ORDER BY %s" % \
        (db.db.quote_name(ordered_obj.pk.column),
        db.db.quote_name(ordered_obj.db_table),
        db.db.quote_name(ordered_obj.order_with_respect_to.column),
        db.db.quote_name('_order'))
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.execute(sql, [rel_val])
    return [r[0] for r in cursor.fetchall()]

# DATE-RELATED METHODS #####################

def method_get_next_or_previous(get_object_func, opts, field, is_next, self, **kwargs):
    op = is_next and '>' or '<'
    kwargs.setdefault('where', []).append('(%s %s %%s OR (%s = %%s AND %s.%s %s %%s))' % \
        (db.db.quote_name(field.column), op, db.db.quote_name(field.column),
        db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column), op))
    param = str(getattr(self, field.attname))
    kwargs.setdefault('params', []).extend([param, param, getattr(self, opts.pk.attname)])
    kwargs['order_by'] = [(not is_next and '-' or '') + field.name, (not is_next and '-' or '') + opts.pk.name]
    kwargs['limit'] = 1
    return get_object_func(**kwargs)

# CHOICE-RELATED METHODS ###################

def method_get_display_value(field, self):
    value = getattr(self, field.attname)
    return dict(field.choices).get(value, value)

# FILE-RELATED METHODS #####################

def method_get_file_filename(field, self):
    return os.path.join(settings.MEDIA_ROOT, getattr(self, field.attname))

def method_get_file_url(field, self):
    if getattr(self, field.attname): # value is not blank
        import urlparse
        return urlparse.urljoin(settings.MEDIA_URL, getattr(self, field.attname)).replace('\\', '/')
    return ''

def method_get_file_size(field, self):
    return os.path.getsize(method_get_file_filename(field, self))

def method_save_file(field, self, filename, raw_contents):
    directory = field.get_directory_name()
    try: # Create the date-based directory if it doesn't exist.
        os.makedirs(os.path.join(settings.MEDIA_ROOT, directory))
    except OSError: # Directory probably already exists.
        pass
    filename = field.get_filename(filename)

    # If the filename already exists, keep adding an underscore to the name of
    # the file until the filename doesn't exist.
    while os.path.exists(os.path.join(settings.MEDIA_ROOT, filename)):
        try:
            dot_index = filename.rindex('.')
        except ValueError: # filename has no dot
            filename += '_'
        else:
            filename = filename[:dot_index] + '_' + filename[dot_index:]

    # Write the file to disk.
    setattr(self, field.attname, filename)
    fp = open(getattr(self, 'get_%s_filename' % field.name)(), 'wb')
    fp.write(raw_contents)
    fp.close()

    # Save the width and/or height, if applicable.
    if isinstance(field, ImageField) and (field.width_field or field.height_field):
        from django.utils.images import get_image_dimensions
        width, height = get_image_dimensions(getattr(self, 'get_%s_filename' % field.name)())
        if field.width_field:
            setattr(self, field.width_field, width)
        if field.height_field:
            setattr(self, field.height_field, height)

    # Save the object, because it has changed.
    self.save()

# IMAGE FIELD METHODS ######################

def method_get_image_width(field, self):
    return _get_image_dimensions(field, self)[0]

def method_get_image_height(field, self):
    return _get_image_dimensions(field, self)[1]

def _get_image_dimensions(field, self):
    cachename = "__%s_dimensions_cache" % field.name
    if not hasattr(self, cachename):
        from django.utils.images import get_image_dimensions
        fname = getattr(self, "get_%s_filename" % field.name)()
        setattr(self, cachename, get_image_dimensions(fname))
    return getattr(self, cachename)

##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self)

def _get_where_clause(lookup_type, table_prefix, field_name, value):
    if table_prefix.endswith('.'):
        table_prefix = db.db.quote_name(table_prefix[:-1])+'.'
    field_name = db.db.quote_name(field_name)
    try:
        return '%s%s %s' % (table_prefix, field_name, (db.OPERATOR_MAPPING[lookup_type] % '%s'))
    except KeyError:
        pass
    if lookup_type == 'in':
        return '%s%s IN (%s)' % (table_prefix, field_name, ','.join(['%s' for v in value]))
    elif lookup_type in ('range', 'year'):
        return '%s%s BETWEEN %%s AND %%s' % (table_prefix, field_name)
    elif lookup_type in ('month', 'day'):
        return "%s = %%s" % db.get_date_extract_sql(lookup_type, table_prefix + field_name)
    elif lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))
    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def function_get_object(opts, klass, does_not_exist_exception, **kwargs):
    obj_list = function_get_list(opts, klass, **kwargs)
    if len(obj_list) < 1:
        raise does_not_exist_exception, "%s does not exist for %s" % (opts.object_name, kwargs)
    assert len(obj_list) == 1, "get_object() returned more than one %s -- it returned %s! Lookup parameters were %s" % (opts.object_name, len(obj_list), kwargs)
    return obj_list[0]

def _get_cached_row(opts, row, index_start):
    "Helper function that recursively returns an object with cache filled"
    index_end = index_start + len(opts.fields)
    obj = opts.get_model_module().Klass(*row[index_start:index_end])
    for f in opts.fields:
        if f.rel and not f.null:
            rel_obj, index_end = _get_cached_row(f.rel.to, row, index_end)
            setattr(obj, f.get_cache_name(), rel_obj)
    return obj, index_end

def function_get_iterator(opts, klass, **kwargs):
    # kwargs['select'] is a dictionary, and dictionaries' key order is
    # undefined, so we convert it to a list of tuples internally.
    kwargs['select'] = kwargs.get('select', {}).items()

    cursor = db.db.cursor()
    select, sql, params = function_get_sql_clause(opts, **kwargs)
    cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
    fill_cache = kwargs.get('select_related')
    index_end = len(opts.fields)
    while 1:
        rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
        if not rows:
            raise StopIteration
        for row in rows:
            if fill_cache:
                obj, index_end = _get_cached_row(opts, row, 0)
            else:
                obj = klass(*row[:index_end])
            for i, k in enumerate(kwargs['select']):
                setattr(obj, k[0], row[index_end+i])
            yield obj

def function_get_list(opts, klass, **kwargs):
    return list(function_get_iterator(opts, klass, **kwargs))

def function_get_count(opts, **kwargs):
    kwargs['order_by'] = []
    kwargs['offset'] = None
    kwargs['limit'] = None
    kwargs['select_related'] = False
    _, sql, params = function_get_sql_clause(opts, **kwargs)
    cursor = db.db.cursor()
    cursor.execute("SELECT COUNT(*)" + sql, params)
    return cursor.fetchone()[0]

def function_get_values_iterator(opts, klass, **kwargs):
    # select_related and select aren't supported in get_values().
    kwargs['select_related'] = False
    kwargs['select'] = {}

    # 'fields' is a list of field names to fetch.
    try:
        fields = [opts.get_field(f).column for f in kwargs.pop('fields')]
    except KeyError: # Default to all fields.
        fields = [f.column for f in opts.fields]

    cursor = db.db.cursor()
    _, sql, params = function_get_sql_clause(opts, **kwargs)
    select = ['%s.%s' % (db.db.quote_name(opts.db_table), db.db.quote_name(f)) for f in fields]
    cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
    while 1:
        rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
        if not rows:
            raise StopIteration
        for row in rows:
            yield dict(zip(fields, row))

def function_get_values(opts, klass, **kwargs):
    return list(function_get_values_iterator(opts, klass, **kwargs))

def _fill_table_cache(opts, select, tables, where, old_prefix, cache_tables_seen):
    """
    Helper function that recursively populates the select, tables and where (in
    place) for fill-cache queries.
    """
    for f in opts.fields:
        if f.rel and not f.null:
            db_table = f.rel.to.db_table
            if db_table not in cache_tables_seen:
                tables.append(db.db.quote_name(db_table))
            else: # The table was already seen, so give it a table alias.
                new_prefix = '%s%s' % (db_table, len(cache_tables_seen))
                tables.append('%s %s' % (db.db.quote_name(db_table), db.db.quote_name(new_prefix)))
                db_table = new_prefix
            cache_tables_seen.append(db_table)
            where.append('%s.%s = %s.%s' % \
                (db.db.quote_name(old_prefix), db.db.quote_name(f.column),
                db.db.quote_name(db_table), db.db.quote_name(f.rel.get_related_field().column)))
            select.extend(['%s.%s' % (db.db.quote_name(db_table), db.db.quote_name(f2.column)) for f2 in f.rel.to.fields])
            _fill_table_cache(f.rel.to, select, tables, where, db_table, cache_tables_seen)

def _throw_bad_kwarg_error(kwarg):
    # Helper function to remove redundancy.
    raise TypeError, "got unexpected keyword argument '%s'" % kwarg

def _parse_lookup(kwarg_items, opts, table_count=0):
    # Helper function that handles converting API kwargs (e.g.
    # "name__exact": "tom") to SQL.

    # Note that there is a distinction between where and join_where. The latter
    # is specifically a list of where clauses to use for JOINs. This
    # distinction is necessary because of support for "_or".

    # table_count is used to ensure table aliases are unique.
    tables, join_where, where, params = [], [], [], []
    for kwarg, kwarg_value in kwarg_items:
        if kwarg in ('order_by', 'limit', 'offset', 'select_related', 'distinct', 'select', 'tables', 'where', 'params'):
            continue
        if kwarg_value is None:
            continue
        if kwarg == 'complex':
            tables2, join_where2, where2, params2, table_count = kwarg_value.get_sql(opts, table_count)
            tables.extend(tables2)
            join_where.extend(join_where2)
            where.extend(where2)
            params.extend(params2)
            continue
        if kwarg == '_or':
            for val in kwarg_value:
                tables2, join_where2, where2, params2, table_count = _parse_lookup(val, opts, table_count)
                tables.extend(tables2)
                join_where.extend(join_where2)
                where.append('(%s)' % ' OR '.join(where2))
                params.extend(params2)
            continue
        lookup_list = kwarg.split(LOOKUP_SEPARATOR)
        # pk="value" is shorthand for (primary key)__exact="value"
        if lookup_list[-1] == 'pk':
            if opts.pk.rel:
                lookup_list = lookup_list[:-1] + [opts.pk.name, opts.pk.rel.field_name, 'exact']
            else:
                lookup_list = lookup_list[:-1] + [opts.pk.name, 'exact']
        if len(lookup_list) == 1:
            _throw_bad_kwarg_error(kwarg)
        lookup_type = lookup_list.pop()
        current_opts = opts # We'll be overwriting this, so keep a reference to the original opts.
        current_table_alias = current_opts.db_table
        param_required = False
        while lookup_list or param_required:
            table_count += 1
            try:
                # "current" is a piece of the lookup list. For example, in
                # choices.get_list(poll__sites__id__exact=5), lookup_list is
                # ["polls", "sites", "id"], and the first current is "polls".
                try:
                    current = lookup_list.pop(0)
                except IndexError:
                    # If we're here, lookup_list is empty but param_required
                    # is set to True, which means the kwarg was bad.
                    # Example: choices.get_list(poll__exact='foo')
                    _throw_bad_kwarg_error(kwarg)
                # Try many-to-many relationships first...
                for f in current_opts.many_to_many:
                    if f.name == current:
                        rel_table_alias = db.db.quote_name('t%s' % table_count)
                        table_count += 1
                        tables.append('%s %s' % \
                            (db.db.quote_name(f.get_m2m_db_table(current_opts)), rel_table_alias))
                        join_where.append('%s.%s = %s.%s' % \
                            (db.db.quote_name(current_table_alias),
                            db.db.quote_name(current_opts.pk.column),
                            rel_table_alias,
                            db.db.quote_name(current_opts.object_name.lower() + '_id')))
                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to.pk.name and lookup_type == 'exact':
                            where.append(_get_where_clause(lookup_type, rel_table_alias+'.',
                                f.rel.to.object_name.lower()+'_id', kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        else:
                            new_table_alias = 't%s' % table_count
                            tables.append('%s %s' % (db.db.quote_name(f.rel.to.db_table),
                                db.db.quote_name(new_table_alias)))
                            join_where.append('%s.%s = %s.%s' % \
                                (db.db.quote_name(rel_table_alias),
                                db.db.quote_name(f.rel.to.object_name.lower() + '_id'),
                                db.db.quote_name(new_table_alias),
                                db.db.quote_name(f.rel.to.pk.column)))
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to
                        raise StopIteration
                for f in current_opts.fields:
                    # Try many-to-one relationships...
                    if f.rel and f.name == current:
                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to.pk.name and lookup_type == 'exact':
                            where.append(_get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        # 'isnull' lookups in many-to-one relationships are a special case,
                        # because we don't want to do a join. We just want to find out
                        # whether the foreign key field is NULL.
                        elif lookup_type == 'isnull' and not lookup_list:
                            where.append(_get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                        else:
                            new_table_alias = 't%s' % table_count
                            tables.append('%s %s' % \
                                (db.db.quote_name(f.rel.to.db_table), db.db.quote_name(new_table_alias)))
                            join_where.append('%s.%s = %s.%s' % \
                                (db.db.quote_name(current_table_alias), db.db.quote_name(f.column),
                                db.db.quote_name(new_table_alias), db.db.quote_name(f.rel.to.pk.column)))
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to
                        raise StopIteration
                    # Try direct field-name lookups...
                    if f.name == current:
                        where.append(_get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                        params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                        param_required = False
                        raise StopIteration
                # If we haven't hit StopIteration at this point, "current" must be
                # an invalid lookup, so raise an exception.
                _throw_bad_kwarg_error(kwarg)
            except StopIteration:
                continue
    return tables, join_where, where, params, table_count

def function_get_sql_clause(opts, **kwargs):
    def quote_only_if_word(word):
        if ' ' in word:
            return word
        else:
            return db.db.quote_name(word)

    # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
    select = ["%s.%s" % (db.db.quote_name(opts.db_table), db.db.quote_name(f.column)) for f in opts.fields]
    tables = [opts.db_table] + (kwargs.get('tables') and kwargs['tables'][:] or [])
    tables = [quote_only_if_word(t) for t in tables]
    where = kwargs.get('where') and kwargs['where'][:] or []
    params = kwargs.get('params') and kwargs['params'][:] or []

    # Convert the kwargs into SQL.
    tables2, join_where2, where2, params2, _ = _parse_lookup(kwargs.items(), opts)
    tables.extend(tables2)
    where.extend(join_where2 + where2)
    params.extend(params2)

    # Add any additional constraints from the "where_constraints" parameter.
    where.extend(opts.where_constraints)

    # Add additional tables and WHERE clauses based on select_related.
    if kwargs.get('select_related') is True:
        _fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])

    # Add any additional SELECTs passed in via kwargs.
    if kwargs.get('select'):
        select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), db.db.quote_name(s[0])) for s in kwargs['select']])

    # ORDER BY clause
    order_by = []
    for f in handle_legacy_orderlist(kwargs.get('order_by', opts.ordering)):
        if f == '?': # Special case.
            order_by.append(db.get_random_function_sql())
        else:
            if f.startswith('-'):
                col_name = f[1:]
                order = "DESC"
            else:
                col_name = f
                order = "ASC"
            if "." in col_name:
                table_prefix, col_name = col_name.split('.', 1)
                table_prefix = db.db.quote_name(table_prefix) + '.'
            else:
                # Use the database table as a column prefix if it wasn't given,
                # and if the requested column isn't a custom SELECT.
                if "." not in col_name and col_name not in [k[0] for k in kwargs.get('select', [])]:
                    table_prefix = db.db.quote_name(opts.db_table) + '.'
                else:
                    table_prefix = ''
            order_by.append('%s%s %s' % (table_prefix, db.db.quote_name(orderfield2column(col_name, opts)), order))
    order_by = ", ".join(order_by)

    # LIMIT and OFFSET clauses
    if kwargs.get('limit') is not None:
        limit_sql = " %s " % db.get_limit_offset_sql(kwargs['limit'], kwargs.get('offset'))
    else:
        assert kwargs.get('offset') is None, "'offset' is not allowed without 'limit'"
        limit_sql = ""

    return select, " FROM " + ",".join(tables) + (where and " WHERE " + " AND ".join(where) or "") + (order_by and " ORDER BY " + order_by or "") + limit_sql, params

def function_get_in_bulk(opts, klass, *args, **kwargs):
    id_list = args and args[0] or kwargs.get('id_list', [])
    assert id_list != [], "get_in_bulk() cannot be passed an empty list."
    kwargs['where'] = ["%s.%s IN (%s)" % (db.db.quote_name(opts.db_table), db.db.quote_name(opts.pk.column), ",".join(['%s'] * len(id_list)))]
    kwargs['params'] = id_list
    obj_list = function_get_list(opts, klass, **kwargs)
    return dict([(getattr(o, opts.pk.attname), o) for o in obj_list])

def function_get_latest(opts, klass, does_not_exist_exception, **kwargs):
    kwargs['order_by'] = ('-' + opts.get_latest_by,)
    kwargs['limit'] = 1
    return function_get_object(opts, klass, does_not_exist_exception, **kwargs)

def function_get_date_list(opts, field, *args, **kwargs):
    from django.core.db.typecasts import typecast_timestamp
    kind = args and args[0] or kwargs['kind']
    assert kind in ("month", "year", "day"), "'kind' must be one of 'year', 'month' or 'day'."
    order = 'ASC'
    if kwargs.has_key('_order'):
        order = kwargs['_order']
        del kwargs['_order']
    assert order in ('ASC', 'DESC'), "'order' must be either 'ASC' or 'DESC'"
    kwargs['order_by'] = [] # Clear this because it'll mess things up otherwise.
    if field.null:
        kwargs.setdefault('where', []).append('%s.%s IS NOT NULL' % \
            (db.db.quote_name(opts.db_table), db.db.quote_name(field.column)))
    select, sql, params = function_get_sql_clause(opts, **kwargs)
    sql = 'SELECT %s %s GROUP BY 1 ORDER BY 1' % (db.get_date_trunc_sql(kind, '%s.%s' % (db.db.quote_name(opts.db_table), db.db.quote_name(field.column))), sql)
    cursor = db.db.cursor()
    cursor.execute(sql, params)
    # We have to manually run typecast_timestamp(str()) on the results, because
    # MySQL doesn't automatically cast the result of date functions as datetime
    # objects -- MySQL returns the values as strings, instead.
    return [typecast_timestamp(str(row[0])) for row in cursor.fetchall()]

###################################
# HELPER FUNCTIONS (MANIPULATORS) #
###################################

def get_manipulator(opts, klass, extra_methods, add=False, change=False):
    "Returns the custom Manipulator (either add or change) for the given opts."
    assert (add == False or change == False) and add != change, "get_manipulator() can be passed add=True or change=True, but not both"
    man = types.ClassType('%sManipulator%s' % (opts.object_name, add and 'Add' or 'Change'), (formfields.Manipulator,), {})
    man.__module__ = MODEL_PREFIX + '.' + opts.module_name # Set this explicitly, as above.
    man.__init__ = curry(manipulator_init, opts, add, change)
    man.save = curry(manipulator_save, opts, klass, add, change)
    man.get_related_objects = curry(manipulator_get_related_objects, opts, klass, add, change)
    man.flatten_data = curry(manipulator_flatten_data, opts, klass, add, change)
    for field_name_list in opts.unique_together:
        setattr(man, 'isUnique%s' % '_'.join(field_name_list), curry(manipulator_validator_unique_together, field_name_list, opts))
    for f in opts.fields:
        if f.unique_for_date:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_date), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_date), opts, 'date'))
        if f.unique_for_month:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_month), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_month), opts, 'month'))
        if f.unique_for_year:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_year), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_year), opts, 'year'))
    for k, v in extra_methods.items():
        setattr(man, k, v)
    return man

def manipulator_init(opts, add, change, self, obj_key=None, follow=None):
    self.follow = opts.get_follow(follow)

    if change:
        assert obj_key is not None, "ChangeManipulator.__init__() must be passed obj_key parameter."
        self.obj_key = obj_key
        try:
            self.original_object = opts.get_model_module().get_object(pk=obj_key)
        except ObjectDoesNotExist:
            # If the object doesn't exist, this might be a manipulator for a
            # one-to-one related object that hasn't created its subobject yet.
            # For example, this might be a Restaurant for a Place that doesn't
            # yet have restaurant information.
            if opts.one_to_one_field:
                # Sanity check -- Make sure the "parent" object exists.
                # For example, make sure the Place exists for the Restaurant.
                # Let the ObjectDoesNotExist exception propogate up.
                lookup_kwargs = opts.one_to_one_field.rel.limit_choices_to
                lookup_kwargs['%s__exact' % opts.one_to_one_field.rel.field_name] = obj_key
                _ = opts.one_to_one_field.rel.to.get_model_module().get_object(**lookup_kwargs)
                params = dict([(f.attname, f.get_default()) for f in opts.fields])
                params[opts.pk.attname] = obj_key
                self.original_object = opts.get_model_module().Klass(**params)
            else:
                raise
    self.fields = []

    for f in opts.fields + opts.many_to_many:
        if self.follow.get(f.name, False):
            self.fields.extend(f.get_manipulator_fields(opts, self, change))

    # Add fields for related objects.
    for f in opts.get_all_related_objects():
        if self.follow.get(f.name, False):
            fol = self.follow[f.name]
            self.fields.extend(f.get_manipulator_fields(opts, self, change, fol))

    # Add field for ordering.
    if change and opts.get_ordered_objects():
        self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

def manipulator_save(opts, klass, add, change, self, new_data):
    # TODO: big cleanup when core fields go -> use recursive manipulators.
    from django.utils.datastructures import DotExpandedDict
    params = {}
    for f in opts.fields:
        # Fields with auto_now_add should keep their original value in the change stage.
        auto_now_add = change and getattr(f, 'auto_now_add', False)
        if self.follow.get(f.name, None) and not auto_now_add:
            param = f.get_manipulator_new_data(new_data)
        else:
            if change:
                param = getattr(self.original_object, f.attname)
            else:
                param = f.get_default()
        params[f.attname] = param

    if change:
        params[opts.pk.attname] = self.obj_key

    # First, save the basic object itself.
    new_object = klass(**params)
    new_object.save()

    # Now that the object's been saved, save any uploaded files.
    for f in opts.fields:
        if isinstance(f, FileField):
            f.save_file(new_data, new_object, change and self.original_object or None, change, rel=False)

    # Calculate which primary fields have changed.
    if change:
        self.fields_added, self.fields_changed, self.fields_deleted = [], [], []
        for f in opts.fields:
            if not f.primary_key and str(getattr(self.original_object, f.attname)) != str(getattr(new_object, f.attname)):
                self.fields_changed.append(f.verbose_name)

    # Save many-to-many objects. Example: Poll.set_sites()
    for f in opts.many_to_many:
        if self.follow.get(f.name, None):
            if not f.rel.edit_inline:
                if f.rel.raw_id_admin:
                    new_vals = new_data.get(f.name, ())
                else:
                    new_vals = new_data.getlist(f.name)
                was_changed = getattr(new_object, 'set_%s' % f.name)(new_vals)
                if change and was_changed:
                    self.fields_changed.append(f.verbose_name)

    expanded_data = DotExpandedDict(dict(new_data))
    # Save many-to-one objects. Example: Add the Choice objects for a Poll.
    for related in opts.get_all_related_objects():
        # Create obj_list, which is a DotExpandedDict such as this:
        # [('0', {'id': ['940'], 'choice': ['This is the first choice']}),
        #  ('1', {'id': ['941'], 'choice': ['This is the second choice']}),
        #  ('2', {'id': [''], 'choice': ['']})]
        child_follow = self.follow.get(related.name, None)

        if child_follow:
            obj_list = expanded_data[related.var_name].items()
            obj_list.sort(lambda x, y: cmp(int(x[0]), int(y[0])))

            # For each related item...
            for _, rel_new_data in obj_list:

                params = {}

                # Keep track of which core=True fields were provided.
                # If all core fields were given, the related object will be saved.
                # If none of the core fields were given, the object will be deleted.
                # If some, but not all, of the fields were given, the validator would
                # have caught that.
                all_cores_given, all_cores_blank = True, True

                # Get a reference to the old object. We'll use it to compare the
                # old to the new, to see which fields have changed.
                old_rel_obj = None
                if change:
                    if rel_new_data[related.opts.pk.name][0]:
                        try:
                            old_rel_obj = getattr(self.original_object, 'get_%s' % related.get_method_name_part() )(**{'%s__exact' % related.opts.pk.name: rel_new_data[related.opts.pk.attname][0]})
                        except ObjectDoesNotExist:
                            pass

                for f in related.opts.fields:
                    if f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) in (None, ''):
                        all_cores_given = False
                    elif f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) not in (None, ''):
                        all_cores_blank = False
                    # If this field isn't editable, give it the same value it had
                    # previously, according to the given ID. If the ID wasn't
                    # given, use a default value. FileFields are also a special
                    # case, because they'll be dealt with later.

                    if f == related.field:
                        param = getattr(new_object, related.field.rel.field_name)
                    elif add and isinstance(f, AutoField):
                        param = None
                    elif change and (isinstance(f, FileField) or not child_follow.get(f.name, None)):
                        if old_rel_obj:
                            param = getattr(old_rel_obj, f.column)
                        else:
                            param = f.get_default()
                    else:
                        param = f.get_manipulator_new_data(rel_new_data, rel=True)
                    if param != None:
                       params[f.attname] = param

                    # Related links are a special case, because we have to
                    # manually set the "content_type_id" and "object_id" fields.
                    if opts.has_related_links and related.opts.module_name == 'relatedlinks':
                        contenttypes_mod = get_module('core', 'contenttypes')
                        params['content_type_id'] = contenttypes_mod.get_object(package__label__exact=opts.app_label, python_module_name__exact=opts.module_name).id
                        params['object_id'] = new_object.id

                # Create the related item.
                new_rel_obj = related.opts.get_model_module().Klass(**params)

                # If all the core fields were provided (non-empty), save the item.
                if all_cores_given:
                    new_rel_obj.save()

                    # Save any uploaded files.
                    for f in related.opts.fields:
                        if child_follow.get(f.name, None):
                            if isinstance(f, FileField) and rel_new_data.get(f.name, False):
                                f.save_file(rel_new_data, new_rel_obj, change and old_rel_obj or None, old_rel_obj is not None, rel=True)

                    # Calculate whether any fields have changed.
                    if change:
                        if not old_rel_obj: # This object didn't exist before.
                            self.fields_added.append('%s "%s"' % (related.opts.verbose_name, new_rel_obj))
                        else:
                            for f in related.opts.fields:
                                if not f.primary_key and f != related.field and str(getattr(old_rel_obj, f.attname)) != str(getattr(new_rel_obj, f.attname)):
                                    self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, related.opts.verbose_name, new_rel_obj))

                    # Save many-to-many objects.
                    for f in related.opts.many_to_many:
                        if child_follow.get(f.name, None) and not f.rel.edit_inline:
                            was_changed = getattr(new_rel_obj, 'set_%s' % f.name)(rel_new_data[f.attname])
                            if change and was_changed:
                                self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, related.opts.verbose_name, new_rel_obj))

                # If, in the change stage, all of the core fields were blank and
                # the primary key (ID) was provided, delete the item.
                if change and all_cores_blank and old_rel_obj:
                    new_rel_obj.delete()
                    self.fields_deleted.append('%s "%s"' % (related.opts.verbose_name, old_rel_obj))

    # Save the order, if applicable.
    if change and opts.get_ordered_objects():
        order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
        for rel_opts in opts.get_ordered_objects():
            getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)
    return new_object

def manipulator_get_related_objects(opts, klass, add, change, self):
    return opts.get_followed_related_objects(self.follow)

def manipulator_flatten_data(opts, klass, add, change, self):
     new_data = {}
     obj = change and self.original_object or None
     for f in opts.get_data_holders(self.follow):
        fol = self.follow.get(f.name)
        new_data.update(f.flatten_data(fol, obj))
     return new_data

def manipulator_validator_unique_together(field_name_list, opts, self, field_data, all_data):
    from django.utils.text import get_text_list
    field_list = [opts.get_field(field_name) for field_name in field_name_list]
    if isinstance(field_list[0].rel, ManyToOne):
        kwargs = {'%s__%s__iexact' % (field_name_list[0], field_list[0].rel.field_name): field_data}
    else:
        kwargs = {'%s__iexact' % field_name_list[0]: field_data}
    for f in field_list[1:]:
        # This is really not going to work for fields that have different
        # form fields, e.g. DateTime.
        # This validation needs to occur after html2python to be effective.
        field_val = all_data.get(f.attname, None)
        if field_val is None:
            # This will be caught by another validator, assuming the field
            # doesn't have blank=True.
            return
        if isinstance(f.rel, ManyToOne):
            kwargs['%s__pk' % f.name] = field_val
        else:
            kwargs['%s__iexact' % f.name] = field_val
    mod = opts.get_model_module()
    try:
        old_obj = mod.get_object(**kwargs)
    except ObjectDoesNotExist:
        return
    if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.attname) == getattr(old_obj, opts.pk.attname):
        pass
    else:
        raise validators.ValidationError, _("%(object)s with this %(type)s already exists for the given %(field)s.") % {
            'object': capfirst(opts.verbose_name), 'type': field_list[0].verbose_name, 'field': get_text_list(field_name_list[1:], 'and')}

def manipulator_validator_unique_for_date(from_field, date_field, opts, lookup_type, self, field_data, all_data):
    date_str = all_data.get(date_field.get_manipulator_field_names('')[0], None)
    mod = opts.get_model_module()
    date_val = formfields.DateField.html2python(date_str)
    if date_val is None:
        return # Date was invalid. This will be caught by another validator.
    lookup_kwargs = {'%s__year' % date_field.name: date_val.year}
    if isinstance(from_field.rel, ManyToOne):
        lookup_kwargs['%s__pk' % from_field.name] = field_data
    else:
        lookup_kwargs['%s__iexact' % from_field.name] = field_data
    if lookup_type in ('month', 'date'):
        lookup_kwargs['%s__month' % date_field.name] = date_val.month
    if lookup_type == 'date':
        lookup_kwargs['%s__day' % date_field.name] = date_val.day
    try:
        old_obj = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        return
    else:
        if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.attname) == getattr(old_obj, opts.pk.attname):
            pass
        else:
            format_string = (lookup_type == 'date') and '%B %d, %Y' or '%B %Y'
            raise validators.ValidationError, "Please enter a different %s. The one you entered is already being used for %s." % \
                (from_field.verbose_name, date_val.strftime(format_string))
