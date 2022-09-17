from django.db.models.fields import Field
from django.db.models.query_utils import DeferredAttribute

class CompositeType:
    _composite_type = None
    _instance = None
    _repr_fmt = '()'
    _fields = ()

    @classmethod
    def namedtuple(cls, name, fields):
        fields = tuple(fields)
        class_namespace = {
            '__doc__': name + '(' + ','.join(fields) + ')',
            '_repr_fmt': '(' + ', '.join(f'{name}=%r' for name in fields) + ')',
            '__slots__': ("_instance",),
            '_fields': fields,
        }
        def bind_property(name):
            def fget(self):
                return getattr(self._instance, name)
            def fset(self, value):
                return setattr(self._instance, name, value)
            return property(fget, fset, doc=f"Bind for field {name}")
        for field in fields:
            class_namespace[field] = bind_property(field)
        return type(name, (cls,), class_namespace)

    def __init__(self, instance):
        self._instance = instance

    def __repr__(self):
            'Return a nicely formatted representation string'
            return self.__class__.__name__ + self._repr_fmt % tuple(self)

    def _asdict(self):
        'Return a new dict which maps field names to their values.'
        return dict(zip(self._fields, self))

    def __len__(self):
        return len(self._fields)

    def __iter__(self):
        return (getattr(self._instance, name) for name in self._fields)

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    def __getitem__(self, i):
        return getattr(self._instance, self._fields[i])

    def __setitem__(self, i, v):
        return setattr(self._instance, self._fields[i], v)

class CompositeDeferredAttribute(DeferredAttribute):
    def _bind(self, instance, cls):
        if issubclass(cls, CompositeType):
            return cls(instance)
        vals = [getattr(instance, name) for name in self.field.names]
        return cls(*vals)
    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        data = instance.__dict__
        field_name = self.field.attname
        if field_name not in data:
            data[field_name] = self._bind(instance, cls=self.field.python_type)
        return data[field_name]

    def __set__(self, instance, value):
        # logger.info(f"set field {self.field} of {instance.__class__.__name__} to {value}")
        data = instance.__dict__
        for name, val in zip(self.field.names, value):
            # logger.info(f"set field {name} of {instance.__class__.__name__} to {val}")
            data[name] = val

class CompositeField(Field):
    names = None
    python_type = tuple

    descriptor_class = CompositeDeferredAttribute
    def __init__(self, *names, **kwargs):
        super().__init__(**kwargs, db_column=None, auto_created=True, editable=False)
        self.names = names
        # self.columns = None

    def get_attname_column(self):
        return self.get_attname(), self.db_column

    def contribute_to_class(self, cls, name, private_only=False) -> None:
        # logger.info(f"{cls.__name__} {name} {cls._meta} {self}")
        self.python_type = CompositeType.namedtuple(f"{cls.__name__}__{name}", list(self.names))
        result = super().contribute_to_class(cls, name, private_only)
        setattr(cls, self.attname, self.descriptor_class(self))

        if self.primary_key:
            cls._meta.pk = self
        if self.unique or self.primary_key:
            cls._meta.unique_together = (*cls._meta.unique_together, tuple(self.names))

            # logger.info(f"{cls.__name__}: unique {cls._meta.unique_together}")
        if self.db_index:
            cls._meta.index_together = (*cls._meta.index_together, tuple(self.names))

        return result
