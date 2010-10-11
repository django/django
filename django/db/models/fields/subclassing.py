"""
Convenience routines for creating non-trivial Field subclasses, as well as
backwards compatibility utilities.

Add SubfieldBase as the __metaclass__ for your Field subclass, implement
to_python() and the other necessary methods and everything will work seamlessly.
"""

from inspect import getargspec
from warnings import warn

def call_with_connection(func):
    arg_names, varargs, varkwargs, defaults = getargspec(func)
    updated = ('connection' in arg_names or varkwargs)
    if not updated:
        warn("A Field class whose %s method hasn't been updated to take a "
            "`connection` argument." % func.__name__,
            DeprecationWarning, stacklevel=2)

    def inner(*args, **kwargs):
        if 'connection' not in kwargs:
            from django.db import connection
            kwargs['connection'] = connection
            warn("%s has been called without providing a connection argument. " %
                func.__name__, DeprecationWarning,
                stacklevel=1)
        if updated:
            return func(*args, **kwargs)
        if 'connection' in kwargs:
            del kwargs['connection']
        return func(*args, **kwargs)
    return inner

def call_with_connection_and_prepared(func):
    arg_names, varargs, varkwargs, defaults = getargspec(func)
    updated = (
        ('connection' in arg_names or varkwargs) and
        ('prepared' in arg_names or varkwargs)
    )
    if not updated:
        warn("A Field class whose %s method hasn't been updated to take "
            "`connection` and `prepared` arguments." % func.__name__,
            DeprecationWarning, stacklevel=2)

    def inner(*args, **kwargs):
        if 'connection' not in kwargs:
            from django.db import connection
            kwargs['connection'] = connection
            warn("%s has been called without providing a connection argument. " %
                func.__name__, DeprecationWarning,
                stacklevel=1)
        if updated:
            return func(*args, **kwargs)
        if 'connection' in kwargs:
            del kwargs['connection']
        if 'prepared' in kwargs:
            del kwargs['prepared']
        return func(*args, **kwargs)
    return inner

class LegacyConnection(type):
    """
    A metaclass to normalize arguments give to the get_db_prep_* and db_type
    methods on fields.
    """
    def __new__(cls, names, bases, attrs):
        new_cls = super(LegacyConnection, cls).__new__(cls, names, bases, attrs)
        for attr in ('db_type', 'get_db_prep_save'):
            setattr(new_cls, attr, call_with_connection(getattr(new_cls, attr)))
        for attr in ('get_db_prep_lookup', 'get_db_prep_value'):
            setattr(new_cls, attr, call_with_connection_and_prepared(getattr(new_cls, attr)))
        return new_cls

class SubfieldBase(LegacyConnection):
    """
    A metaclass for custom Field subclasses. This ensures the model's attribute
    has the descriptor protocol attached to it.
    """
    def __new__(cls, base, name, attrs):
        new_class = super(SubfieldBase, cls).__new__(cls, base, name, attrs)
        new_class.contribute_to_class = make_contrib(
                attrs.get('contribute_to_class'))
        return new_class

class Creator(object):
    """
    A placeholder class that provides a way to set the attribute on the model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = self.field.to_python(value)

def make_contrib(func=None):
    """
    Returns a suitable contribute_to_class() method for the Field subclass.

    If 'func' is passed in, it is the existing contribute_to_class() method on
    the subclass and it is called before anything else. It is assumed in this
    case that the existing contribute_to_class() calls all the necessary
    superclass methods.
    """
    def contribute_to_class(self, cls, name):
        if func:
            func(self, cls, name)
        else:
            super(self.__class__, self).contribute_to_class(cls, name)
        setattr(cls, self.name, Creator(self))

    return contribute_to_class
