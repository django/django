import django.db.models.manipulators
import django.db.models.manager
from django.db.models.fields import AutoField, ImageField
from django.db.models.fields.related import OneToOne, ManyToOne
from django.db.models.related import RelatedObject
from django.db.models.query import orderlist2sql
from django.db.models.options import Options, AdminOptions
from django.db import connection, backend
from django.db.models import signals
from django.dispatch import dispatcher
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import curry
from django.conf import settings
import re
import types
import sys
import os

# For Python 2.3
if not hasattr(__builtins__, 'set'):
    from sets import Set as set

class ModelBase(type):
    "Metaclass for all models"
    def __new__(cls, name, bases, attrs):
        # If this isn't a subclass of Model, don't do anything special.
        if not bases or bases == (object,):
            return type.__new__(cls, name, bases, attrs)

        # Create the class.
        new_class = type.__new__(cls, name, bases, {'__module__': attrs.pop('__module__')})
        new_class.add_to_class('_meta', Options(attrs.pop('Meta', None)))
        new_class.add_to_class('DoesNotExist', types.ClassType('DoesNotExist', (ObjectDoesNotExist,), {}))

        model_module = sys.modules[new_class.__module__]

        # Figure out the app_label by looking one level up.
        # For 'django.contrib.sites.models', this would be 'sites'.
        app_label = model_module.__name__.split('.')[-2]

        # Cache the app label.
        new_class._meta.app_label = app_label

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        new_class._prepare()

        # Populate the _MODELS member on the module the class is in.
        model_module.__dict__.setdefault('_MODELS', []).append(new_class)
        return new_class

def cmp_cls(x, y):
    for field in x._meta.fields:
        if field.rel and not field.null and field.rel.to == y:
            return -1
    for field in y._meta.fields:
        if field.rel and not field.null and field.rel.to == x:
            return 1
    return 0

class Model(object):
    __metaclass__ = ModelBase

    def _get_pk_val(self):
        return getattr(self, self._meta.pk.attname)

    def __repr__(self):
        return '<%s object>' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._get_pk_val() == other._get_pk_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __init__(self, *args, **kwargs):
        dispatcher.send(signal=signals.pre_init, sender=self.__class__, args=args, kwargs=kwargs)
        if kwargs:
            for f in self._meta.fields:
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
            setattr(self, self._meta.fields[i].attname, arg)
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
                db_values = [f.get_db_prep_save(f.pre_save(getattr(self, f.attname), False)) for f in non_pks]
                cursor.execute("UPDATE %s SET %s WHERE %s=%%s" % \
                    (backend.quote_name(self._meta.db_table),
                    ','.join(['%s=%%s' % backend.quote_name(f.column) for f in non_pks]),
                    backend.quote_name(self._meta.pk.attname)),
                    db_values + [pk_val])
            else:
                record_exists = False
        if not pk_set or not record_exists:
            field_names = [backend.quote_name(f.column) for f in self._meta.fields if not isinstance(f, AutoField)]
            db_values = [f.get_db_prep_save(f.pre_save(getattr(self, f.attname), True)) for f in self._meta.fields if not isinstance(f, AutoField)]
            # If the PK has been manually set, respect that.
            if pk_set:
                field_names += [f.column for f in self._meta.fields if isinstance(f, AutoField)]
                db_values += [f.get_db_prep_save(f.pre_save(getattr(self, f.column), True)) for f in self._meta.fields if isinstance(f, AutoField)]
            placeholders = ['%s'] * len(field_names)
            if self._meta.order_with_respect_to:
                field_names.append(backend.quote_name('_order'))
                # TODO: This assumes the database supports subqueries.
                placeholders.append('(SELECT COUNT(*) FROM %s WHERE %s = %%s)' % \
                    (backend.quote_name(self._meta.db_table), backend.quote_name(self._meta.order_with_respect_to.column)))
                db_values.append(getattr(self, self._meta.order_with_respect_to.attname))
            cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
                (backend.quote_name(self._meta.db_table), ','.join(field_names),
                ','.join(placeholders)), db_values)
            if self._meta.has_auto_field and not pk_set:
                setattr(self, self._meta.pk.attname, backend.get_last_insert_id(cursor, self._meta.db_table, self._meta.pk.column))
        connection.commit()

        # Run any post-save hooks.
        dispatcher.send(signal=signals.pre_save, sender=self.__class__, instance=self)

    save.alters_data = True

    def __collect_sub_objects(self, seen_objs):
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
            if isinstance(related.field.rel, OneToOne):
                try:
                    sub_obj = getattr(self, rel_opts_name)
                except ObjectDoesNotExist:
                    pass
                else:
                    sub_obj.__collect_sub_objects(seen_objs)
            else:
                for sub_obj in getattr(self, rel_opts_name).all():
                    sub_obj.__collect_sub_objects(seen_objs)

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        seen_objs = {}
        self.__collect_sub_objects(seen_objs)

        seen_classes = set(seen_objs.keys())
        ordered_classes = list(seen_classes)
        ordered_classes.sort(cmp_cls)

        cursor = connection.cursor()

        for cls in ordered_classes:
            seen_objs[cls] = seen_objs[cls].items()
            seen_objs[cls].sort()
            for pk_val, instance in seen_objs[cls]:
                dispatcher.send(signal=signals.pre_delete, sender=cls, instance=instance)

                for related in cls._meta.get_all_related_many_to_many_objects():
                    cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
                        (backend.quote_name(related.field.get_m2m_db_table(related.opts)),
                        backend.quote_name(cls._meta.object_name.lower() + '_id')),
                        [pk_val])
                for f in cls._meta.many_to_many:
                    cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
                        (backend.quote_name(f.get_m2m_db_table(cls._meta)),
                        backend.quote_name(cls._meta.object_name.lower() + '_id')),
                        [pk_val])
                for field in cls._meta.fields:
                    if field.rel and field.null and field.rel.to in seen_classes:
                        cursor.execute("UPDATE %s SET %s=NULL WHERE %s=%%s" % \
                            (backend.quote_name(cls._meta.db_table), backend.quote_name(field.column),
                            backend.quote_name(cls._meta.pk.column)), [pk_val])
                        setattr(instance, field.attname, None)

        for cls in ordered_classes:
            seen_objs[cls].reverse()
            for pk_val, instance in seen_objs[cls]:
                cursor.execute("DELETE FROM %s WHERE %s=%%s" % \
                    (backend.quote_name(cls._meta.db_table), backend.quote_name(cls._meta.pk.column)),
                    [pk_val])
                setattr(instance, cls._meta.pk.attname, None)
                dispatcher.send(signal=signals.post_delete, sender=cls, instance=instance)

        connection.commit()

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
        q = self.__class__._default_manager.order_by((not is_next and '-' or '') + field.name, (not is_next and '-' or '') + self._meta.pk.name)
        q._where.append(where)
        q._params.extend([param, param, getattr(self, self._meta.pk.attname)])
        return q[0]

    def _get_next_or_previous_in_order(self, is_next):
        cachename = "__%s_order_cache" % is_next
        if not hasattr(self, cachename):
            op = is_next and '>' or '<'
            order_field = self.order_with_respect_to
            obj = self._default_manager.get_object(order_by=('_order',),
                where=['%s %s (SELECT %s FROM %s WHERE %s=%%s)' % \
                    (backend.quote_name('_order'), op, backend.quote_name('_order'),
                    backend.quote_name(opts.db_table), backend.quote_name(opts.pk.column)),
                    '%s=%%s' % backend.quote_name(order_field.column)],
                limit=1,
                params=[self._get_pk_val(), getattr(self, order_field.attname)])
            setattr(self, cachename, obj)
        return getattr(self, cachename)

    def _get_FIELD_filename(self, field):
        return os.path.join(settings.MEDIA_ROOT, getattr(self, field.attname))

    def _get_FIELD_url(self, field):
        if getattr(self, field.attname): # value is not blank
            import urlparse
            return urlparse.urljoin(settings.MEDIA_URL, getattr(self, field.attname)).replace('\\', '/')
        return ''

    def _get_FIELD_size(self, field):
        return os.path.getsize(self.__get_FIELD_filename(field))

    def _save_FIELD_file(self, field, filename, raw_contents):
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

        # Save the object, because it has changed.
        self.save()

    _save_FIELD_file.alters_data = True

    def _get_FIELD_width(self, field):
        return self.__get_image_dimensions(field)[0]

    def _get_FIELD_height(self, field):
        return self.__get_image_dimensions(field)[1]

    def _get_image_dimensions(self, field):
        cachename = "__%s_dimensions_cache" % field.name
        if not hasattr(self, cachename):
            from django.utils.images import get_image_dimensions
            filename = self.__get_FIELD_filename(field)()
            setattr(self, cachename, get_image_dimensions(filename))
        return getattr(self, cachename)

    def _set_many_to_many_objects(self, id_list, field_with_rel):
        current_ids = [obj._get_pk_val() for obj in self._get_many_to_many_objects(field_with_rel)]
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
        rel = field_with_rel.rel.to._meta
        m2m_table = field_with_rel.get_m2m_db_table(self._meta)
        cursor = connection.cursor()
        this_id = self._get_pk_val()
        if ids_to_delete:
            sql = "DELETE FROM %s WHERE %s = %%s AND %s IN (%s)" % \
                (backend.quote_name(m2m_table),
                backend.quote_name(self._meta.object_name.lower() + '_id'),
                backend.quote_name(rel.object_name.lower() + '_id'), ','.join(map(str, ids_to_delete)))
            cursor.execute(sql, [this_id])
        if ids_to_add:
            sql = "INSERT INTO %s (%s, %s) VALUES (%%s, %%s)" % \
                (backend.quote_name(m2m_table),
                backend.quote_name(self._meta.object_name.lower() + '_id'),
                backend.quote_name(rel.object_name.lower() + '_id'))
            cursor.executemany(sql, [(this_id, i) for i in ids_to_add])
        connection.commit()
        try:
            delattr(self, '_%s_cache' % field_with_rel.name) # clear cache, if it exists
        except AttributeError:
            pass
        return True

    _set_many_to_many_objects.alters_data = True

    # Handles setting many-to-many related objects.
    # Example: Album.set_songs()
    def _set_related_many_to_many(self, rel_class, rel_field, id_list):
        id_list = map(int, id_list) # normalize to integers
        rel = rel_field.rel.to
        m2m_table = rel_field.get_m2m_db_table(rel_opts)
        this_id = self._get_pk_val()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM %s WHERE %s = %%s" % \
            (backend.quote_name(m2m_table),
            backend.quote_name(rel.object_name.lower() + '_id')), [this_id])
        sql = "INSERT INTO %s (%s, %s) VALUES (%%s, %%s)" % \
            (backend.quote_name(m2m_table),
            backend.quote_name(rel.object_name.lower() + '_id'),
            backend.quote_name(rel_opts.object_name.lower() + '_id'))
        cursor.executemany(sql, [(this_id, i) for i in id_list])
        connection.commit()

############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list):
    cursor = connection.cursor()
    # Example: "UPDATE poll_choices SET _order = %s WHERE poll_id = %s AND id = %s"
    sql = "UPDATE %s SET %s = %%s WHERE %s = %%s AND %s = %%s" % \
        (backend.quote_name(ordered_obj.db_table), backend.quote_name('_order'),
        backend.quote_name(ordered_obj.order_with_respect_to.column),
        backend.quote_name(ordered_obj.pk.column))
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.executemany(sql, [(i, rel_val, j) for i, j in enumerate(id_list)])
    connection.commit()

def method_get_order(ordered_obj, self):
    cursor = connection.cursor()
    # Example: "SELECT id FROM poll_choices WHERE poll_id = %s ORDER BY _order"
    sql = "SELECT %s FROM %s WHERE %s = %%s ORDER BY %s" % \
        (backend.quote_name(ordered_obj.pk.column),
        backend.quote_name(ordered_obj.db_table),
        backend.quote_name(ordered_obj.order_with_respect_to.column),
        backend.quote_name('_order'))
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.execute(sql, [rel_val])
    return [r[0] for r in cursor.fetchall()]

##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self)
