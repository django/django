import django.db.models.manipulators
import django.db.models.manager
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import AutoField, ImageField, FieldDoesNotExist
from django.db.models.fields.related import OneToOneRel, ManyToOneRel
from django.db.models.query import delete_objects
from django.db.models.options import Options, AdminOptions
from django.db import connection, backend, transaction
from django.db.models import signals
from django.db.models.loading import register_models, get_model
from django.dispatch import dispatcher
from django.utils.datastructures import SortedDict
from django.utils.functional import curry
from django.conf import settings
from itertools import izip
import types
import sys
import os

class ModelBase(type):
    "Metaclass for all models"
    def __new__(cls, name, bases, attrs):
        # If this isn't a subclass of Model, don't do anything special.
        try:
            if not filter(lambda b: issubclass(b, Model), bases):
                return super(ModelBase, cls).__new__(cls, name, bases, attrs)
        except NameError:
            # 'Model' isn't defined yet, meaning we're looking at Django's own
            # Model class, defined below.
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)

        # Create the class.
        new_class = type.__new__(cls, name, bases, {'__module__': attrs.pop('__module__')})
        new_class.add_to_class('_meta', Options(attrs.pop('Meta', None)))
        new_class.add_to_class('DoesNotExist', types.ClassType('DoesNotExist', (ObjectDoesNotExist,), {}))

        # Build complete list of parents
        for base in bases:
            # TODO: Checking for the presence of '_meta' is hackish.
            if '_meta' in dir(base):
                new_class._meta.parents.append(base)
                new_class._meta.parents.extend(base._meta.parents)

        model_module = sys.modules[new_class.__module__]

        if getattr(new_class._meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            new_class._meta.app_label = model_module.__name__.split('.')[-2]

        # Bail out early if we have already created this class.
        m = get_model(new_class._meta.app_label, name, False)
        if m is not None:
            return m

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        # Add Fields inherited from parents
        for parent in new_class._meta.parents:
            for field in parent._meta.fields:
                # Only add parent fields if they aren't defined for this class.
                try:
                    new_class._meta.get_field(field.name)
                except FieldDoesNotExist:
                    field.contribute_to_class(new_class, field.name)

        new_class._prepare()

        register_models(new_class._meta.app_label, new_class)
        # Because of the way imports happen (recursively), we may or may not be
        # the first class for this model to register with the framework. There
        # should only be one class for each model, so we must always return the
        # registered version.
        return get_model(new_class._meta.app_label, name, False)

class Model(object):
    __metaclass__ = ModelBase

    def _get_pk_val(self):
        return getattr(self, self._meta.pk.attname)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    def __str__(self):
        return '%s object' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._get_pk_val() == other._get_pk_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __init__(self, *args, **kwargs):
        dispatcher.send(signal=signals.pre_init, sender=self.__class__, args=args, kwargs=kwargs)
        
        # There is a rather weird disparity here; if kwargs, it's set, then args
        # overrides it. It should be one or the other; don't duplicate the work 
        # The reason for the kwargs check is that standard iterator passes in by
        # args, and nstantiation for iteration is 33% faster.
        args_len = len(args)
        if args_len > len(self._meta.fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")

        fields_iter = iter(self._meta.fields)
        if not kwargs:
            # The ordering of the izip calls matter - izip throws StopIteration
            # when an iter throws it. So if the first iter throws it, the second
            # is *not* consumed. We rely on this, so don't change the order
            # without changing the logic.
            for val, field in izip(args, fields_iter):
                setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            for val, field in izip(args, fields_iter):
                setattr(self, field.attname, val)
                kwargs.pop(field.name, None)
                # Maintain compatibility with existing calls.
                if isinstance(field.rel, ManyToOneRel):
                    kwargs.pop(field.attname, None)
        
        # Now we're left with the unprocessed fields that *must* come from
        # keywords, or default.
        
        for field in fields_iter:
            if kwargs:
                if isinstance(field.rel, ManyToOneRel):
                    try:
                        # Assume object instance was passed in.
                        rel_obj = kwargs.pop(field.name)
                    except KeyError:
                        try:
                            # Object instance wasn't passed in -- must be an ID.
                            val = kwargs.pop(field.attname)
                        except KeyError:
                            val = field.get_default()
                    else:
                        # Object instance was passed in. Special case: You can
                        # pass in "None" for related objects if it's allowed.
                        if rel_obj is None and field.null:
                            val = None
                        else:
                            try:
                                val = getattr(rel_obj, field.rel.get_related_field().attname)
                            except AttributeError:
                                raise TypeError("Invalid value: %r should be a %s instance, not a %s" % 
                                    (field.name, field.rel.to, type(rel_obj)))
                else:
                    val = kwargs.pop(field.attname, field.get_default())
            else:
                val = field.get_default()
            setattr(self, field.attname, val)

        if kwargs:
            for prop in kwargs.keys():
                try:
                    if isinstance(getattr(self.__class__, prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                raise TypeError, "'%s' is an invalid keyword argument for this function" % kwargs.keys()[0]
        dispatcher.send(signal=signals.post_init, sender=self.__class__, instance=self)

    def add_to_class(cls, name, value):
        if name == 'Admin':
            assert type(value) == types.ClassType, "%r attribute of %s model must be a class, not a %s object" % (name, cls.__name__, type(value))
            value = AdminOptions(**dict([(k, v) for k, v in value.__dict__.items() if not k.startswith('_')]))
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)
    add_to_class = classmethod(add_to_class)

    def _prepare(cls):
        # Creates some methods once self._meta has been populated.
        opts = cls._meta
        opts._prepare(cls)

        if opts.order_with_respect_to:
            cls.get_next_in_order = curry(cls._get_next_or_previous_in_order, is_next=True)
            cls.get_previous_in_order = curry(cls._get_next_or_previous_in_order, is_next=False)
            setattr(opts.order_with_respect_to.rel.to, 'get_%s_order' % cls.__name__.lower(), curry(method_get_order, cls))
            setattr(opts.order_with_respect_to.rel.to, 'set_%s_order' % cls.__name__.lower(), curry(method_set_order, cls))

        # Give the class a docstring -- its definition.
        if cls.__doc__ is None:
            cls.__doc__ = "%s(%s)" % (cls.__name__, ", ".join([f.attname for f in opts.fields]))

        if hasattr(cls, 'get_absolute_url'):
            cls.get_absolute_url = curry(get_absolute_url, opts, cls.get_absolute_url)

        dispatcher.send(signal=signals.class_prepared, sender=cls)

    _prepare = classmethod(_prepare)

    def save(self):
        dispatcher.send(signal=signals.pre_save, sender=self.__class__, instance=self)

        non_pks = [f for f in self._meta.fields if not f.primary_key]
        cursor = connection.cursor()

        # First, try an UPDATE. If that doesn't update anything, do an INSERT.
        pk_val = self._get_pk_val()
        pk_set = bool(pk_val)
        record_exists = True
        if pk_set:
            # Determine whether a record with the primary key already exists.
            cursor.execute("SELECT 1 FROM %s WHERE %s=%%s LIMIT 1" % \
                (backend.quote_name(self._meta.db_table), backend.quote_name(self._meta.pk.column)), [pk_val])
            # If it does already exist, do an UPDATE.
            if cursor.fetchone():
                db_values = [f.get_db_prep_save(f.pre_save(self, False)) for f in non_pks]
                if db_values:
                    cursor.execute("UPDATE %s SET %s WHERE %s=%%s" % \
                        (backend.quote_name(self._meta.db_table),
                        ','.join(['%s=%%s' % backend.quote_name(f.column) for f in non_pks]),
                        backend.quote_name(self._meta.pk.column)),
                        db_values + [pk_val])
            else:
                record_exists = False
        if not pk_set or not record_exists:
            field_names = [backend.quote_name(f.column) for f in self._meta.fields if not isinstance(f, AutoField)]
            db_values = [f.get_db_prep_save(f.pre_save(self, True)) for f in self._meta.fields if not isinstance(f, AutoField)]
            # If the PK has been manually set, respect that.
            if pk_set:
                field_names += [f.column for f in self._meta.fields if isinstance(f, AutoField)]
                db_values += [f.get_db_prep_save(f.pre_save(self, True)) for f in self._meta.fields if isinstance(f, AutoField)]
            placeholders = ['%s'] * len(field_names)
            if self._meta.order_with_respect_to:
                field_names.append(backend.quote_name('_order'))
                # TODO: This assumes the database supports subqueries.
                placeholders.append('(SELECT COUNT(*) FROM %s WHERE %s = %%s)' % \
                    (backend.quote_name(self._meta.db_table), backend.quote_name(self._meta.order_with_respect_to.column)))
                db_values.append(getattr(self, self._meta.order_with_respect_to.attname))
            if db_values:
                cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
                    (backend.quote_name(self._meta.db_table), ','.join(field_names),
                    ','.join(placeholders)), db_values)
            else:
                # Create a new record with defaults for everything.
                cursor.execute("INSERT INTO %s (%s) VALUES (%s)" %
                    (backend.quote_name(self._meta.db_table),
                     backend.quote_name(self._meta.pk.column),
                     backend.get_pk_default_value()))
            if self._meta.has_auto_field and not pk_set:
                setattr(self, self._meta.pk.attname, backend.get_last_insert_id(cursor, self._meta.db_table, self._meta.pk.column))
        transaction.commit_unless_managed()

        # Run any post-save hooks.
        dispatcher.send(signal=signals.post_save, sender=self.__class__, instance=self)

    save.alters_data = True

    def validate(self):
        """
        First coerces all fields on this instance to their proper Python types.
        Then runs validation on every field. Returns a dictionary of
        field_name -> error_list.
        """
        error_dict = {}
        invalid_python = {}
        for f in self._meta.fields:
            try:
                setattr(self, f.attname, f.to_python(getattr(self, f.attname, f.get_default())))
            except validators.ValidationError, e:
                error_dict[f.name] = e.messages
                invalid_python[f.name] = 1
        for f in self._meta.fields:
            if f.name in invalid_python:
                continue
            errors = f.validate_full(getattr(self, f.attname, f.get_default()), self.__dict__)
            if errors:
                error_dict[f.name] = errors
        return error_dict

    def _collect_sub_objects(self, seen_objs):
        """
        Recursively populates seen_objs with all objects related to this object.
        When done, seen_objs will be in the format:
            {model_class: {pk_val: obj, pk_val: obj, ...},
             model_class: {pk_val: obj, pk_val: obj, ...}, ...}
        """
        pk_val = self._get_pk_val()
        if pk_val in seen_objs.setdefault(self.__class__, {}):
            return
        seen_objs.setdefault(self.__class__, {})[pk_val] = self

        for related in self._meta.get_all_related_objects():
            rel_opts_name = related.get_accessor_name()
            if isinstance(related.field.rel, OneToOneRel):
                try:
                    sub_obj = getattr(self, rel_opts_name)
                except ObjectDoesNotExist:
                    pass
                else:
                    sub_obj._collect_sub_objects(seen_objs)
            else:
                for sub_obj in getattr(self, rel_opts_name).all():
                    sub_obj._collect_sub_objects(seen_objs)

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)

        # Find all the objects than need to be deleted
        seen_objs = SortedDict()
        self._collect_sub_objects(seen_objs)

        # Actually delete the objects
        delete_objects(seen_objs)

    delete.alters_data = True

    def _get_FIELD_display(self, field):
        value = getattr(self, field.attname)
        return dict(field.choices).get(value, value)

    def _get_next_or_previous_by_FIELD(self, field, is_next, **kwargs):
        op = is_next and '>' or '<'
        where = '(%s %s %%s OR (%s = %%s AND %s.%s %s %%s))' % \
            (backend.quote_name(field.column), op, backend.quote_name(field.column),
            backend.quote_name(self._meta.db_table), backend.quote_name(self._meta.pk.column), op)
        param = str(getattr(self, field.attname))
        q = self.__class__._default_manager.filter(**kwargs).order_by((not is_next and '-' or '') + field.name, (not is_next and '-' or '') + self._meta.pk.name)
        q._where.append(where)
        q._params.extend([param, param, getattr(self, self._meta.pk.attname)])
        try:
            return q[0]
        except IndexError:
            raise self.DoesNotExist, "%s matching query does not exist." % self.__class__._meta.object_name

    def _get_next_or_previous_in_order(self, is_next):
        cachename = "__%s_order_cache" % is_next
        if not hasattr(self, cachename):
            op = is_next and '>' or '<'
            order_field = self._meta.order_with_respect_to
            where = ['%s %s (SELECT %s FROM %s WHERE %s=%%s)' % \
                (backend.quote_name('_order'), op, backend.quote_name('_order'),
                backend.quote_name(self._meta.db_table), backend.quote_name(self._meta.pk.column)),
                '%s=%%s' % backend.quote_name(order_field.column)]
            params = [self._get_pk_val(), getattr(self, order_field.attname)]
            obj = self._default_manager.order_by('_order').extra(where=where, params=params)[:1].get()
            setattr(self, cachename, obj)
        return getattr(self, cachename)

    def _get_FIELD_filename(self, field):
        if getattr(self, field.attname): # value is not blank
            return os.path.join(settings.MEDIA_ROOT, getattr(self, field.attname))
        return ''

    def _get_FIELD_url(self, field):
        if getattr(self, field.attname): # value is not blank
            import urlparse
            return urlparse.urljoin(settings.MEDIA_URL, getattr(self, field.attname)).replace('\\', '/')
        return ''

    def _get_FIELD_size(self, field):
        return os.path.getsize(self._get_FIELD_filename(field))

    def _save_FIELD_file(self, field, filename, raw_contents, save=True):
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

        full_filename = self._get_FIELD_filename(field)
        fp = open(full_filename, 'wb')
        fp.write(raw_contents)
        fp.close()

        # Save the width and/or height, if applicable.
        if isinstance(field, ImageField) and (field.width_field or field.height_field):
            from django.utils.images import get_image_dimensions
            width, height = get_image_dimensions(full_filename)
            if field.width_field:
                setattr(self, field.width_field, width)
            if field.height_field:
                setattr(self, field.height_field, height)

        # Save the object because it has changed unless save is False
        if save:
            self.save()

    _save_FIELD_file.alters_data = True

    def _get_FIELD_width(self, field):
        return self._get_image_dimensions(field)[0]

    def _get_FIELD_height(self, field):
        return self._get_image_dimensions(field)[1]

    def _get_image_dimensions(self, field):
        cachename = "__%s_dimensions_cache" % field.name
        if not hasattr(self, cachename):
            from django.utils.images import get_image_dimensions
            filename = self._get_FIELD_filename(field)
            setattr(self, cachename, get_image_dimensions(filename))
        return getattr(self, cachename)

############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list):
    cursor = connection.cursor()
    # Example: "UPDATE poll_choices SET _order = %s WHERE poll_id = %s AND id = %s"
    sql = "UPDATE %s SET %s = %%s WHERE %s = %%s AND %s = %%s" % \
        (backend.quote_name(ordered_obj._meta.db_table), backend.quote_name('_order'),
        backend.quote_name(ordered_obj._meta.order_with_respect_to.column),
        backend.quote_name(ordered_obj._meta.pk.column))
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    cursor.executemany(sql, [(i, rel_val, j) for i, j in enumerate(id_list)])
    transaction.commit_unless_managed()

def method_get_order(ordered_obj, self):
    cursor = connection.cursor()
    # Example: "SELECT id FROM poll_choices WHERE poll_id = %s ORDER BY _order"
    sql = "SELECT %s FROM %s WHERE %s = %%s ORDER BY %s" % \
        (backend.quote_name(ordered_obj._meta.pk.column),
        backend.quote_name(ordered_obj._meta.db_table),
        backend.quote_name(ordered_obj._meta.order_with_respect_to.column),
        backend.quote_name('_order'))
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    cursor.execute(sql, [rel_val])
    return [r[0] for r in cursor.fetchall()]

##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self)
