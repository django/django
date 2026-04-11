# $Id: __init__.py 10146 2025-05-27 06:14:22Z milde $
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

from __future__ import annotations

__docformat__ = 'reStructuredText'

import warnings

from docutils import languages, ApplicationError, TransformSpec


class TransformError(ApplicationError):
    pass


class Transform:
    """Docutils transform component abstract base class."""

    default_priority = None
    """Numerical priority of this transform, 0 through 999 (override)."""

    def __init__(self, document, startnode=None) -> None:
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
    Store "transforms" and apply them to the document tree.

    Collect lists of `Transform` instances from Docutils
    components (`TransformSpec` instances).
    Apply collected "transforms" to the document tree.

    Also keeps track of components by component type name.

    https://docutils.sourceforge.io/docs/peps/pep-0258.html#transformer
    """

    def __init__(self, document) -> None:
        self.transforms = []
        """List of transforms to apply.  Each item is a 4-tuple:
        ``(priority string, transform class, pending node or None, kwargs)``.
        """

        self.unknown_reference_resolvers = []
        """List of hook functions which assist in resolving references.

        Deprecated. Will be removed in Docutils 1.0.
        """

        self.document = document
        """The `nodes.document` object this Transformer is attached to."""

        self.applied = []
        """Transforms already applied, in order."""

        self.sorted = False
        """Boolean: is `self.tranforms` sorted?"""

        self.components = {}
        """Mapping of component type name to component object.

        Set by `self.populate_from_components()`.
        """

        self.serialno = 0
        """Internal serial number to keep track of the add order of
        transforms."""

    def add_transform(self, transform_class, priority=None, **kwargs) -> None:
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
        self.sorted = False

    def add_transforms(self, transform_list) -> None:
        """Store multiple transforms, with default priorities."""
        for transform_class in transform_list:
            priority_string = self.get_priority_string(
                transform_class.default_priority)
            self.transforms.append(
                (priority_string, transform_class, None, {}))
        self.sorted = False

    def add_pending(self, pending, priority=None) -> None:
        """Store a transform with an associated `pending` node."""
        transform_class = pending.transform
        if priority is None:
            priority = transform_class.default_priority
        priority_string = self.get_priority_string(priority)
        self.transforms.append(
            (priority_string, transform_class, pending, {}))
        self.sorted = False

    def get_priority_string(self, priority) -> str:
        """
        Return a string, `priority` combined with `self.serialno`.

        This ensures FIFO order on transforms with identical priority.
        """
        self.serialno += 1
        return '%03d-%03d' % (priority, self.serialno)

    def populate_from_components(self, components) -> None:
        """
        Store each component's default transforms and reference resolvers.

        Transforms are stored with default priorities for later sorting.
        "Unknown reference resolvers" are sorted and stored.
        Components that don't inherit from `TransformSpec` are ignored.

        Also, store components by type name in a mapping for later lookup.
        """
        resolvers = []
        for component in components:
            if not isinstance(component, TransformSpec):
                continue
            self.add_transforms(component.get_transforms())
            self.components[component.component_type] = component
            resolvers.extend(component.unknown_reference_resolvers)
        self.sorted = False  # sort transform list in self.apply_transforms()

        # Sort and add hook functions helping to resolve unknown references.
        def keyfun(f):
            return f.priority
        resolvers.sort(key=keyfun)
        self.unknown_reference_resolvers += resolvers
        if self.unknown_reference_resolvers:
            warnings.warn('The `unknown_reference_resolvers` hook chain '
                          'will be removed in Docutils 1.0.\n'
                          'Use a transform to resolve references.',
                          DeprecationWarning, stacklevel=2)

    def apply_transforms(self) -> None:
        """Apply all of the stored transforms, in priority order."""
        self.document.reporter.attach_observer(
            self.document.note_transform_message)
        while self.transforms:
            if not self.sorted:
                # Unsorted initially, and whenever a transform is added
                # (transforms may add other transforms).
                self.transforms.sort(reverse=True)
                self.sorted = True
            priority, transform_class, pending, kwargs = self.transforms.pop()
            transform = transform_class(self.document, startnode=pending)
            transform.apply(**kwargs)
            self.applied.append((priority, transform_class, pending, kwargs))
        self.document.reporter.detach_observer(
            self.document.note_transform_message)
