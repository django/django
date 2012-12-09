"""
"Safe weakrefs", originally from pyDispatcher.

Provides a way to safely weakref any function, including bound methods (which
aren't handled by the core weakref module).
"""

import traceback
import weakref

def safeRef(target, onDelete = None):
    """Return a *safe* weak reference to a callable target

    target -- the object to be weakly referenced, if it's a
        bound method reference, will create a BoundMethodWeakref,
        otherwise creates a simple weakref.
    onDelete -- if provided, will have a hard reference stored
        to the callable to be called after the safe reference
        goes out of scope with the reference object, (either a
        weakref or a BoundMethodWeakref) as argument.
    """
    if hasattr(target, '__self__'):
        if target.__self__ is not None:
            # Turn a bound method into a BoundMethodWeakref instance.
            # Keep track of these instances for lookup by disconnect().
            assert hasattr(target, '__func__'), """safeRef target %r has __self__, but no __func__, don't know how to create reference"""%( target,)
            reference = get_bound_method_weakref(
                target=target,
                onDelete=onDelete
            )
            return reference
    if callable(onDelete):
        return weakref.ref(target, onDelete)
    else:
        return weakref.ref( target )

class BoundMethodWeakref(object):
    """'Safe' and reusable weak references to instance methods

    BoundMethodWeakref objects provide a mechanism for
    referencing a bound method without requiring that the
    method object itself (which is normally a transient
    object) is kept alive.  Instead, the BoundMethodWeakref
    object keeps weak references to both the object and the
    function which together define the instance method.

    Attributes:
        key -- the identity key for the reference, calculated
            by the class's calculateKey method applied to the
            target instance method
        deletionMethods -- sequence of callable objects taking
            single argument, a reference to this object which
            will be called when *either* the target object or
            target function is garbage collected (i.e. when
            this object becomes invalid).  These are specified
            as the onDelete parameters of safeRef calls.
        weakSelf -- weak reference to the target object
        weakFunc -- weak reference to the target function

    Class Attributes:
        _allInstances -- class attribute pointing to all live
            BoundMethodWeakref objects indexed by the class's
            calculateKey(target) method applied to the target
            objects.  This weak value dictionary is used to
            short-circuit creation so that multiple references
            to the same (object, function) pair produce the
            same BoundMethodWeakref instance.

    """

    _allInstances = weakref.WeakValueDictionary()

    def __new__( cls, target, onDelete=None, *arguments,**named ):
        """Create new instance or return current instance

        Basically this method of construction allows us to
        short-circuit creation of references to already-
        referenced instance methods.  The key corresponding
        to the target is calculated, and if there is already
        an existing reference, that is returned, with its
        deletionMethods attribute updated.  Otherwise the
        new instance is created and registered in the table
        of already-referenced methods.
        """
        key = cls.calculateKey(target)
        current =cls._allInstances.get(key)
        if current is not None:
            current.deletionMethods.append( onDelete)
            return current
        else:
            base = super( BoundMethodWeakref, cls).__new__( cls )
            cls._allInstances[key] = base
            base.__init__( target, onDelete, *arguments,**named)
            return base

    def __init__(self, target, onDelete=None):
        """Return a weak-reference-like instance for a bound method

        target -- the instance-method target for the weak
            reference, must have __self__ and __func__ attributes
            and be reconstructable via:
                target.__func__.__get__( target.__self__ )
            which is true of built-in instance methods.
        onDelete -- optional callback which will be called
            when this weak reference ceases to be valid
            (i.e. either the object or the function is garbage
            collected).  Should take a single argument,
            which will be passed a pointer to this object.
        """
        def remove(weak, self=self):
            """Set self.isDead to true when method or instance is destroyed"""
            methods = self.deletionMethods[:]
            del self.deletionMethods[:]
            try:
                del self.__class__._allInstances[ self.key ]
            except KeyError:
                pass
            for function in methods:
                try:
                    if callable( function ):
                        function( self )
                except Exception as e:
                    try:
                        traceback.print_exc()
                    except AttributeError:
                        print('Exception during saferef %s cleanup function %s: %s' % (
                            self, function, e)
                        )
        self.deletionMethods = [onDelete]
        self.key = self.calculateKey( target )
        self.weakSelf = weakref.ref(target.__self__, remove)
        self.weakFunc = weakref.ref(target.__func__, remove)
        self.selfName = str(target.__self__)
        self.funcName = str(target.__func__.__name__)

    def calculateKey( cls, target ):
        """Calculate the reference key for this reference

        Currently this is a two-tuple of the id()'s of the
        target object and the target function respectively.
        """
        return (id(target.__self__),id(target.__func__))
    calculateKey = classmethod( calculateKey )

    def __str__(self):
        """Give a friendly representation of the object"""
        return """%s( %s.%s )"""%(
            self.__class__.__name__,
            self.selfName,
            self.funcName,
        )

    __repr__ = __str__

    __hash__ = object.__hash__

    def __bool__( self ):
        """Whether we are still a valid reference"""
        return self() is not None

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __eq__(self, other):
        """Compare with another reference"""
        if not isinstance(other, self.__class__):
            return self.__class__ == type(other)
        return self.key == other.key

    def __call__(self):
        """Return a strong reference to the bound method

        If the target cannot be retrieved, then will
        return None, otherwise returns a bound instance
        method for our object and function.

        Note:
            You may call this method any number of times,
            as it does not invalidate the reference.
        """
        target = self.weakSelf()
        if target is not None:
            function = self.weakFunc()
            if function is not None:
                return function.__get__(target)
        return None

class BoundNonDescriptorMethodWeakref(BoundMethodWeakref):
    """A specialized BoundMethodWeakref, for platforms where instance methods
    are not descriptors.

    It assumes that the function name and the target attribute name are the
    same, instead of assuming that the function is a descriptor. This approach
    is equally fast, but not 100% reliable because functions can be stored on an
    attribute named differenty than the function's name such as in:

    class A: pass
    def foo(self): return "foo"
    A.bar = foo

    But this shouldn't be a common use case. So, on platforms where methods
    aren't descriptors (such as Jython) this implementation has the advantage
    of working in the most cases.
    """
    def __init__(self, target, onDelete=None):
        """Return a weak-reference-like instance for a bound method

        target -- the instance-method target for the weak
            reference, must have __self__ and __func__ attributes
            and be reconstructable via:
                target.__func__.__get__( target.__self__ )
            which is true of built-in instance methods.
        onDelete -- optional callback which will be called
            when this weak reference ceases to be valid
            (i.e. either the object or the function is garbage
            collected).  Should take a single argument,
            which will be passed a pointer to this object.
        """
        assert getattr(target.__self__, target.__name__) == target, \
               ("method %s isn't available as the attribute %s of %s" %
                (target, target.__name__, target.__self__))
        super(BoundNonDescriptorMethodWeakref, self).__init__(target, onDelete)

    def __call__(self):
        """Return a strong reference to the bound method

        If the target cannot be retrieved, then will
        return None, otherwise returns a bound instance
        method for our object and function.

        Note:
            You may call this method any number of times,
            as it does not invalidate the reference.
        """
        target = self.weakSelf()
        if target is not None:
            function = self.weakFunc()
            if function is not None:
                # Using partial() would be another option, but it erases the
                # "signature" of the function. That is, after a function is
                # curried, the inspect module can't be used to determine how
                # many arguments the function expects, nor what keyword
                # arguments it supports, and pydispatcher needs this
                # information.
                return getattr(target, function.__name__)
        return None

def get_bound_method_weakref(target, onDelete):
    """Instantiates the appropiate BoundMethodWeakRef, depending on the details of
    the underlying class method implementation"""
    if hasattr(target, '__get__'):
        # target method is a descriptor, so the default implementation works:
        return BoundMethodWeakref(target=target, onDelete=onDelete)
    else:
        # no luck, use the alternative implementation:
        return BoundNonDescriptorMethodWeakref(target=target, onDelete=onDelete)
