# $Id: __init__.py 6433 2010-09-28 08:21:25Z milde $
# Authors: David Goodger <goodger@python.org>; Ueli Schlaepfer
# Copyright: This module has been placed in the public domain.

"""
This package contains modules for standard tree transforms available
to Docutils components. Tree transforms serve a variety of purposes:

- To tie up certain syntax-specific "loose ends" that remain after the
  initial parsing of the input plaintext. These transforms are used to
  supplement a limited syntax.

- To automate the internal linking of the document tree (hyperlink
  references, footnote references, etc.).

- To extract useful information from the document tree. These
  transforms may be used to construct (for example) indexes and tables
  of contents.

Each transform is an optional step that a Docutils component may
choose to perform on the parsed document.
"""

__docformat__ = 'reStructuredText'


from docutils import languages, ApplicationError, TransformSpec


class TransformError(ApplicationError): pass


class Transform:

    """
    Docutils transform component abstract base class.
    """

    default_priority = None
    """Numerical priority of this transform, 0 through 999 (override)."""

    def __init__(self, document, startnode=None):
        """
        Initial setup for in-place document transforms.
        """

        self.document = document
        """The document tree to transform."""

        self.startnode = startnode
        """Node from which to begin the transform.  For many transforms which
        apply to the document as a whole, `startnode` is not set (i.e. its
        value is `None`)."""

        self.language = languages.get_language(
            document.settings.language_code, document.reporter)
        """Language module local to this document."""

    def apply(self, **kwargs):
        """Override to apply the transform to the document tree."""
        raise NotImplementedError('subclass must override this method')


class Transformer(TransformSpec):

    """
    Stores transforms (`Transform` classes) and applies them to document
    trees.  Also keeps track of components by component type name.
    """

    def __init__(self, document):
        self.transforms = []
        """List of transforms to apply.  Each item is a 3-tuple:
        ``(priority string, transform class, pending node or None)``."""

        self.unknown_reference_resolvers = []
        """List of hook functions which assist in resolving references"""

        self.document = document
        """The `nodes.document` object this Transformer is attached to."""

        self.applied = []
        """Transforms already applied, in order."""

        self.sorted = 0
        """Boolean: is `self.tranforms` sorted?"""

        self.components = {}
        """Mapping of component type name to component object.  Set by
        `self.populate_from_components()`."""

        self.serialno = 0
        """Internal serial number to keep track of the add order of
        transforms."""

    def add_transform(self, transform_class, priority=None, **kwargs):
        """
        Store a single transform.  Use `priority` to override the default.
        `kwargs` is a dictionary whose contents are passed as keyword
        arguments to the `apply` method of the transform.  This can be used to
        pass application-specific data to the transform instance.
        """
        if priority is None:
            priority = transform_class.default_priority
        priority_string = self.get_priority_string(priority)
        self.transforms.append(
            (priority_string, transform_class, None, kwargs))
        self.sorted = 0

    def add_transforms(self, transform_list):
        """Store multiple transforms, with default priorities."""
        for transform_class in transform_list:
            priority_string = self.get_priority_string(
                transform_class.default_priority)
            self.transforms.append(
                (priority_string, transform_class, None, {}))
        self.sorted = 0

    def add_pending(self, pending, priority=None):
        """Store a transform with an associated `pending` node."""
        transform_class = pending.transform
        if priority is None:
            priority = transform_class.default_priority
        priority_string = self.get_priority_string(priority)
        self.transforms.append(
            (priority_string, transform_class, pending, {}))
        self.sorted = 0

    def get_priority_string(self, priority):
        """
        Return a string, `priority` combined with `self.serialno`.

        This ensures FIFO order on transforms with identical priority.
        """
        self.serialno += 1
        return '%03d-%03d' % (priority, self.serialno)

    def populate_from_components(self, components):
        """
        Store each component's default transforms, with default priorities.
        Also, store components by type name in a mapping for later lookup.
        """
        for component in components:
            if component is None:
                continue
            self.add_transforms(component.get_transforms())
            self.components[component.component_type] = component
        self.sorted = 0
        # Set up all of the reference resolvers for this transformer. Each
        # component of this transformer is able to register its own helper
        # functions to help resolve references.
        unknown_reference_resolvers = []
        for i in components:
            unknown_reference_resolvers.extend(i.unknown_reference_resolvers)
        decorated_list = [(f.priority, f) for f in unknown_reference_resolvers]
        decorated_list.sort()
        self.unknown_reference_resolvers.extend([f[1] for f in decorated_list])

    def apply_transforms(self):
        """Apply all of the stored transforms, in priority order."""
        self.document.reporter.attach_observer(
            self.document.note_transform_message)
        while self.transforms:
            if not self.sorted:
                # Unsorted initially, and whenever a transform is added.
                self.transforms.sort()
                self.transforms.reverse()
                self.sorted = 1
            priority, transform_class, pending, kwargs = self.transforms.pop()
            transform = transform_class(self.document, startnode=pending)
            transform.apply(**kwargs)
            self.applied.append((priority, transform_class, pending, kwargs))
