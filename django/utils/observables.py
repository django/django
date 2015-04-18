import weakref
import collections
import inspect
from django.utils import six


class _NoValue:
    def __repr__(self):
        return 'NO_VALUE'

NO_VALUE = _NoValue()


def _is_descriptor(attribute):
    return any(hasattr(attribute, method)
               for method in {'__get__', '__set__', '__delete__'})


class ChangeRecord(collections.namedtuple(
    'ChangeRecord',
    ('type', 'observable', 'key', 'old', 'new')
)):
    def __new__(cls, type, observable, key, old=NO_VALUE, new=NO_VALUE):
        return super(ChangeRecord, cls).__new__(
            cls, type, observable, key, old, new
        )

    @classmethod
    def item(cls, observable, key, old=NO_VALUE, new=NO_VALUE):
        return cls('item', observable, key, old=old, new=new)

    @classmethod
    def attribute(cls, observable, key, old=NO_VALUE, new=NO_VALUE):
        return cls('attribute', observable, key, old=old, new=new)

    @property
    def type(self):
        """ The type of the change record. Value must be one of:
        - 'item':
            The 'key' of the record represents an index into a sequence or
            a key of a mapping
        - 'attribute':
            The 'key' of the record represents an attribute of an object.
        """
        return super(ChangeRecord, self).type

    @property
    def insert(self):
        return self.old is NO_VALUE

    @property
    def remove(self):
        return self.new is NO_VALUE


class Observable(object):

    def add_observer(self, observer):
        if not hasattr(observer, 'handle_changes'):
            raise TypeError("observer must have a 'handl_changes' method")
        observer_ref = weakref.ref(observer, self._remove_observer_ref)
        self.observer_refs.append(observer_ref)

    @property
    def observer_refs(self):
        """
        Returns a list of weak references to the observers of the observable
        """
        return self.__dict__.setdefault('_observer_refs', list())

    def _remove_observer_ref(self, observer_ref):
        self.observer_refs.remove(observer_ref)

    @property
    def _resolved_attribute_descriptors(self):
        return self.__dict__.setdefault('_attribute_setters', {})

    @property
    def _change_notifier(self):
        return self.__dict__.setdefault(
            '_change_notifier_', ChangeNotifier(self)
        )

    def _resolve_descriptor(self, attr_name):
        for cls in inspect.getmro(type(self)):
            attr = cls.__dict__.get(attr_name, None)
            if attr is None:
                continue
            return attr if _is_descriptor(attr) else None

    def __setattr__(self, attr_name, value):
        old_value = getattr(self, attr_name, NO_VALUE)
        if attr_name not in self.__dict__:
            descriptor = self._resolve_descriptor(attr_name)
            if descriptor is not None:
                if hasattr(descriptor, '__set__'):
                    descriptor.__set__(self, value)
                    return self._attribute_changed(attr_name, old_value, value)
                else:
                    raise AttributeError(
                        "Cannot set attribute '{0}'".format(attr_name)
                    )
        self._attribute_changed(attr_name, old_value, value)
        self.__dict__[attr_name] = value

    def __delattr__(self, attr_name):
        raise NotImplementedError('ObservableMixin.__delattr__')

    def _attribute_changed(self, attr_name, old, new):
        self._change_notifier.deliver(ChangeRecord.attribute(
            self, attr_name, old=old, new=new
        ))


class ObservableList(list, Observable):

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            return self._setitem_slice(index, value)
        with ChangeNotifier(self) as notifier:
            index = self._positive_index(index)
            notifier.deliver(self._mutate_record(index, value))
            super(ObservableList, self).__setitem__(index, value)

    def _setitem_slice(self, slice, value):
        start, stop, step = slice.indices(len(self))
        if step == 1:
            with ChangeNotifier(self) as notifier:
                r = range(start, stop, step)
                # Clear out the list in reverse order so that we don't mess
                # with the indexes of items we remove later
                for i in reversed(r):
                    notifier.deliver(self._remove_record(i))
                # Add all the items back into the list in reversed order
                for item in reversed(value):
                    notifier.deliver(self._insert_record(start, item))
                super(ObservableList, self).__setitem__(slice, value)
        else:
            # If the step isn't one, then the value must be the same length
            # as the slice
            r = range(start, stop, step)
            if len(value) != len(r):
                # Just delegate to super to throw the correct error
                super(ObservableList, self).__setitem__(slice, value)
            # Otherwise just __setitem__ on each value in turn. Zip could return
            # an unexpected error (zip argument #2 does not support iteration)
            # but meh. Who in their right mind uses assignment to a range
            # anyway?
            for i, item in zip(r, value):
                self.__setitem__(i, item)

    def __delitem__(self, index):
        if isinstance(index, slice):
            return self._delitem_slice(index)
        index = self._positive_index(index)
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._remove_record(index))
            super(ObservableList, self).__delitem__(index)

    def _delitem_slice(self, slice):
        start, stop, step = slice.indices(len(self))
        r = range(start, stop, step)
        if step > 0:
            # Reverse the range so that we don't remove lower indexes before
            # higher ones
            r = reversed(r)
        with ChangeNotifier(self) as notifier:
            for i in r:
                notifier.deliver(self._remove_record(i))
            super(ObservableList, self).__delitem__(slice)

    def __iadd__(self, li):
        if not isinstance(li, list):
            raise TypeError(
                'Can only concatenate "list" (not "{0}") to list'
                .format(type(li))
            )
        with ChangeNotifier(self) as notifier:
            _len = len(self)
            for index, item in enumerate(li):
                notifier.deliver(self._insert_record(_len + index, item))
            return super(ObservableList, self).__iadd__(li)

    def __imul__(self, value):
        if not isinstance(value, six.integer_types):
            raise TypeError(
                "Cannot multiply sequence by non-int of type '{0}'"
                .format(type(value))
            )
        if value <= 0:
            self.clear()
        with ChangeNotifier(self) as notifier:
            for i in range(1, value):
                start = i * len(self)
                for index, item in enumerate(self):
                    notifier.deliver(self._insert_record(start + index, item))
            return super(ObservableList, self).__imul__(value)

    def append(self, item):
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._insert_record(len(self), item))
            super(ObservableList, self).append(item)

    def insert(self, index, item):
        index = self._positive_index(index)
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._insert_record(index, item))
            super(ObservableList, self).insert(index, item)

    def extend(self, iterable):
        with ChangeNotifier(self) as notifier:
            for index, item in enumerate(iterable):
                notifier.deliver(self._insert_record(len(self) + index, item))
            super(ObservableList, self).extend(iterable)

    def clear(self):
        with ChangeNotifier(self) as notifier:
            for i in reversed(range(len(self))):
                notifier.deliver(self._remove_record(i))
            super(ObservableList, self).clear()

    def pop(self, index=None):
        if index is None:
            index = len(self) - 1
        index = self._positive_index(index)
        if not isinstance(index, six.integer_types):
            raise TypeError("'{0}' cannot be interpreted as integer"
                            .format(type(index)))
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._remove_record(index))
            return super(ObservableList, self).pop(index)

    def remove(self, value):
        with ChangeNotifier(self) as notifier:
            for i, item in enumerate(self):
                if item == value:
                    notifier.deliver(self._remove_record(i))
            super(ObservableList, self).remove(value)

    def reverse(self):
        """ Reverse *IN PLACE* """
        with ChangeNotifier(self) as notifier:
            last = len(self) - 1
            for i in range(int(len(self) / 2)):
                notifier.deliver(self._mutate_record(i, self[last - i]))
                notifier.deliver(self._mutate_record(last - i, self[i]))
            super(ObservableList, self).reverse()

    def sort(self):
        raise NotImplementedError(
            "in-place sort not implemented for observable lists. "
            "Copy the list using the builtin `sorted` instead"
        )

    def _positive_index(self, index):
        if not isinstance(index, six.integer_types):
            raise TypeError(
                "list indices must be 'int', not '{0}'".format(type(index))
            )
        return len(self) + index if index < 0 else index

    def _mutate_record(self, index, new_value):
        return ChangeRecord.item(self, index, old=self[index], new=new_value)

    def _insert_record(self, index, value):
        return ChangeRecord.item(self, index, new=value)

    def _remove_record(self, index):
        return ChangeRecord.item(self, index, old=self[index])


class _ObservableMapping(Observable):
    def __delitem__(self, key):
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._remove_record(key))
            super(_ObservableMapping, self).__delitem__(key)

    def __setitem__(self, key, value):
        with ChangeNotifier(self) as notifier:
            if key in self:
                notifier.deliver(self._mutate_record(key, value))
            else:
                notifier.deliver(self._insert_record(key, value))
            super(_ObservableMapping, self).__setitem__(key, value)

    def clear(self):
        with ChangeNotifier(self) as notifier:
            for key, value in self.items():
                notifier.deliver(self._remove_record(key, value))
            super(_ObservableMapping, self).clear()

    def pop(self, key):
        with ChangeNotifier(self) as notifier:
            notifier.deliver(self._remove_record(key))
            return super(_ObservableMapping, self).pop(key)

    def popitem(self):
        with ChangeNotifier(self) as notifier:
            k, v = super(_ObservableMapping, self).popitem()
            notifier.deliver(self._remove_record(k, value=v))
            return (k, v)

    def setdefault(self, key, value):
        with ChangeNotifier(self) as notifier:
            if key not in self:
                notifier.deliver(self._insert_record(key, value))
            super(_ObservableMapping, self).setdefault(key, value)

    def update(self, *args, **kwargs):
        # to_update is an OrderedDict so that ObservableOrderedDict doesn't
        # lose the order on update
        to_update = collections.OrderedDict(*args, **kwargs)
        with ChangeNotifier(self) as notifier:
            for k, v in to_update.items():
                if k in self:
                    notifier.deliver(self._mutate_record(k, v))
                else:
                    notifier.deliver(self._insert_record(k, v))
            super(_ObservableMapping, self).update(to_update)

    def _mutate_record(self, key, new):
        return ChangeRecord.item(self, key, old=self[key], new=new)

    def _insert_record(self, key, value):
        return ChangeRecord.item(self, key, new=value)

    def _remove_record(self, key, value=NO_VALUE):
        value = self[key] if value is NO_VALUE else value
        return ChangeRecord.item(self, key, old=value)


class ObservableDict(_ObservableMapping, dict):
    pass


class ObservableOrderedDict(_ObservableMapping, collections.OrderedDict):
    pass


class ChangeNotifier(object):
    """
    An obect which collects and delivers changes for an observable.

    When used as a context manager, this class will batch all delivered requests
    and deliver them as a single group of changes
    """
    def __init__(self, observable):
        self.observable = observable
        self._batch = None

    def __enter__(self):
        self._batch = list()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            self._send_changes(self._batch)
        self._batch = None
        # Don't suppress any exceptions
        return False

    def deliver(self, change_record):
        if self._batch is None:
            self._send_changes([change_record, ])
        else:
            self._batch.append(change_record)

    def _send_changes(self, changes):
        for observer_ref in self.observable.observer_refs:
            observer = observer_ref()
            if observer is None:
                continue
            observer.handle_changes(changes)
