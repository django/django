"""
  This module houses the GEOSPointer class, used by GEOS Geometry objects
   internally for memory management.  Do not modify unless you _really_
   know what you're doing.
"""
from ctypes import cast, c_int, c_void_p, pointer, POINTER, Structure
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import lgeos

# This C data structure houses the memory addresses (integers) of the
#  pointers returned from the GEOS C routines.
class GEOSStruct(Structure): pass
GEOSStruct._fields_ = [("geom", POINTER(c_int)),  # for the geometry
                       ("cs", POINTER(c_int)),    # for geometries w/coordinate sequences
                       ("parent", POINTER(GEOSStruct)), # points to the GEOSStruct of the parent
                       ("child", c_void_p),       # points to an array of GEOSStructs
                       ("nchild", c_int),         # the number of children
                       ]

class GEOSPointer(object):
    """
    The GEOSPointer provides a layer of abstraction in accessing the values 
     returned by GEOS geometry creation routines.  Memory addresses (integers) 
     are kept in a C pointer, which allows parent geometries to be 'nullified' 
     when a child's memory is used in construction of another geometry.

    This object is also used to store pointers for any associated coordinate 
     sequence and may store the pointers for any children geometries.
    """

    #### Python 'magic' routines ####
    def __init__(self, address, coordseq=0):
        """
        Initializes on an address (an integer), another GEOSPointer, or a
         GEOSStruct object.
        """
        if isinstance(address, int):
            self._struct = GEOSStruct()
            # Integer addresses passed in, use the 'set' methods.
            self.set(address)
            if coordseq: self.set_coordseq(coordseq)
        elif isinstance(address, GEOSPointer):
            # Initializing from another GEOSPointer
            self._struct = address._struct
        elif isinstance(address, GEOSStruct):
            # GEOSStruct passed directly in as a parameter
            self._struct = address
        else:
            raise TypeError, 'GEOSPointer object must initialize with an integer.'

    def __call__(self):
        """
        Returns the address value (an integer) of the GEOS Geometry pointer.
         If the pointer is NULL, a GEOSException will be raised, thus preventing
         an invalid memory address from being passed to a C routine.
        """
        if self.valid: return self.address
        else: raise GEOSException, 'GEOS pointer no longer valid (was this geometry or the parent geometry deleted or modified?)'

    def __getitem__(self, index):
        "Returns a GEOSpointer object at the given child index."
        n_child = len(self)
        if n_child:
            if index < 0 or index >= n_child:
                raise IndexError, 'invalid child index'
            else:
                CHILD_PTR = POINTER(GEOSStruct * len(self))
                return GEOSPointer(cast(self._struct.child, CHILD_PTR).contents[index])
        else:
            raise GEOSException, 'This GEOSPointer is not a parent'

    def __iter__(self):
        """
        Iterates over the children Geometry pointers, return as GEOSPointer 
         objects to the caller.
        """
        for i in xrange(len(self)):
            yield self[i]

    def __len__(self):
        "Returns the number of children Geometry pointers (or 0 if no children)."
        return self._struct.nchild

    def __nonzero__(self):
        "Returns True when the GEOSPointer is valid."
        return self.valid

    def __str__(self):
        "Returns the string representation of this GEOSPointer."
        # First getting the address for the Geometry pointer.
        if self.valid: geom_addr = self.address
        else: geom_addr = 0
        # If there's a coordinate sequence, construct accoringly.
        if self.coordseq_valid:
            return 'GEOSPointer(%s, %s)' % (geom_addr, self.coordseq_address)
        else:
            return 'GEOSPointer(%s)' % geom_addr

    def __repr__(self):
        return str(self)

    #### GEOSPointer Properties ####
    @property
    def address(self):
        "Returns the address of the GEOSPointer (represented as an integer)."
        return self._struct.geom.contents.value

    @property
    def valid(self):
        "Tests whether this GEOSPointer is valid."
        return bool(self._struct.geom)

    #### Parent & Child Properties ####
    @property
    def parent(self):
        "Returns the GEOSPointer for the parent or None."
        if self.child:
            return GEOSPointer(self._struct.parent.contents)
        else:
            return None

    @property
    def child(self):
        "Returns True if the GEOSPointer has a parent."
        return bool(self._struct.parent)

    #### Coordinate Sequence routines and properties ####
    def coordseq(self):
        """
        If the coordinate sequence pointer is NULL or 0, an exception will
         be raised.
        """
        if self.coordseq_valid: return self.coordseq_address
        else: raise GEOSException, 'GEOS coordinate sequence pointer invalid (was this geometry or the parent geometry deleted or modified?)'

    @property
    def coordseq_address(self):
        "Returns the address of the related coordinate sequence."
        return self._struct.cs.contents.value

    @property
    def coordseq_valid(self):
        "Returns True if the coordinate sequence address is valid, False otherwise."
        return bool(self._struct.cs)

    #### GEOSPointer Methods ####
    def destroy(self):
        """
        Calls GEOSGeom_destroy on the address of this pointer, and nullifies
         this pointer. Use VERY carefully, as trying to destroy an address that 
         no longer holds a valid GEOS Geometry may crash Python.
        """
        if self.valid:
            # ONLY on valid geometries.
            lgeos.GEOSGeom_destroy(self.address)
            self.nullify()

    def set(self, address):
        """
        Sets the address of this pointer with the given address (represented
         as an integer).  Using 0 or None will set the pointer to NULL.
        """
        if address in (0, None):
            self._struct.geom = None
        else:
            self._struct.geom.contents = c_int(address)

    def set_coordseq(self, address):
        """
        Sets the address of the coordinate sequence associated with
         this pointer.
        """
        if address in (0, None):
            self._struct.cs = None
        else:
            self._struct.cs.contents = c_int(address)

    def set_children(self, ptr_list):
        """
        Sets children pointers with the given pointer list (of integers).
         Alternatively, a list of tuples for the geometry and coordinate
         sequence pointers of the children may be used.
        """
        # The number of children geometries is the number of pointers (or
        #  tuples) passed in via the `ptr_list`.
        n_child = len(ptr_list)

        # Determining whether coordinate sequences pointers were passed in.
        if n_child and isinstance(ptr_list[0], (tuple, list)):
            self._child_cs = True
        else:
            self._child_cs = False

        # Dynamically creating the C types for the children array (CHILD_ARR),
        # initializing with the created type, and creating a parent pointer
        # for the children.
        CHILD_ARR = GEOSStruct * n_child
        children = CHILD_ARR()
        parent = pointer(self._struct)

        # Incrementing through each of the children, and setting the
        #  pointers in the array of GEOSStructs.
        for i in xrange(n_child):
            if self._child_cs:
                geom_ptr, cs_ptr = ptr_list[i]
                if cs_ptr is not None:
                    children[i].cs.contents = c_int(cs_ptr)
            else:
                geom_ptr = ptr_list[i]
            children[i].geom.contents = c_int(geom_ptr)
            children[i].parent = parent

        # Casting the CHILD_ARR to the contents of the void pointer, and 
        #  setting the number of children within the struct (used by __len__).
        self._struct.child = cast(pointer(children), c_void_p)
        self._struct.nchild = c_int(n_child)

    def nullify(self):
        """
        Nullify the geometry and coordinate sequence pointers (sets the
         pointers to NULL).  This does not delete any memory (destroy() 
         handles that), rather, it sets the GEOS pointers to a NULL address, 
         preventing access to deleted objects.
        """
        # Nullifying both the geometry and coordinate sequence pointer.
        self.set(None)
        self.set_coordseq(None)

    def summary(self):
        """
        Returns a summary string containing information about the pointer, 
         including the geometry address, any associated coordinate sequence
         address, and child geometry addresses.
        """
        sum = '%s\n' % str(self)
        for p1 in self: 
            sum += '  * %s\n' % p1
            for p2 in p1: sum += '    - %s\n' %  p2
        if bool(self._struct.parent):
            sum += 'Parent: %s\n' % self.parent
        return sum

class NullGEOSPointer(GEOSPointer):
    "The NullGEOSPointer is always NULL, and cannot be set to anything else."
    def __init__(self):
        self._struct = GEOSStruct()

    @property
    def valid(self):
        return False

    @property
    def coordseq_valid(self):
        return False

    def set(self, *args):
        pass

    def set_coordseq(self, *args):
        pass

    def set_children(self, *args):
        pass

NULL_GEOM = NullGEOSPointer()
