from django.db.models.related import RelatedObject
from django.db.models.fields import OneToOne, ManyToMany
from django.db.models.fields import AutoField
from django.db.models.loading import get_installed_model_modules
from django.db.models.query import orderlist2sql
from django.db.models.exceptions import FieldDoesNotExist

class Options:
    def __init__(self, module_name='', verbose_name='', verbose_name_plural='', db_table='',
        fields=None, ordering=None, unique_together=None, admin=None,
        where_constraints=None, object_name=None, app_label=None,
        exceptions=None, permissions=None, get_latest_by=None,
        order_with_respect_to=None, module_constants=None):
        # Move many-to-many related fields from self.fields into self.many_to_many.
        self.fields, self.many_to_many = [], []
        for field in (fields or []):
            if field.rel and isinstance(field.rel, ManyToMany):
                self.many_to_many.append(field)
            else:
                self.fields.append(field)
        self.module_name, self.verbose_name = module_name, verbose_name
        self.verbose_name_plural = verbose_name_plural or verbose_name + 's'
        self.db_table = db_table
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
        #HACK
        self.limit_choices_to = {}


    def __repr__(self):
        return '<Options for %s>' % self.module_name

   # def get_model_module(self):
   #     return get_module(self.app_label, self.module_name)

    def get_content_type_id(self):
        "Returns the content-type ID for this object type."
        if not hasattr(self, '_content_type_id'):
            import django.models.core
            manager = django.models.core.ContentType.objects
            self._content_type_id = \
                manager.get_object(python_module_name__exact=self.module_name, 
                                   package__label__exact=self.app_label).id
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
                        if f.rel and self == f.rel.to._meta:
                            rel_objs.append(RelatedObject(self, klass, f))
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
                    if f.rel and self == f.rel.to._meta:
                        rel_objs.append(RelatedObject(self, klass, f))
        return rel_objs

    def get_ordered_objects(self):
        "Returns a list of Options objects that are ordered with respect to this object."
        if not hasattr(self, '_ordered_objects'):
            objects = []
            #HACK
            #for klass in get_app(self.app_label)._MODELS:
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