"""Document tree nodes that Sphinx defines on top of those in Docutils."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes

if TYPE_CHECKING:
    from collections.abc import Sequence

    from docutils.nodes import Element

    from sphinx.application import Sphinx

# deprecated name -> (object to return, canonical path or empty string)
_DEPRECATED_OBJECTS = {
    'meta': (nodes.meta, 'docutils.nodes.meta'),  # type: ignore[attr-defined]
    'docutils_meta': (nodes.meta, 'docutils.nodes.meta'),  # type: ignore[attr-defined]
}


def __getattr__(name):
    if name not in _DEPRECATED_OBJECTS:
        msg = f'module {__name__!r} has no attribute {name!r}'
        raise AttributeError(msg)

    from sphinx.deprecation import _deprecation_warning

    deprecated_object, canonical_name = _DEPRECATED_OBJECTS[name]
    _deprecation_warning(__name__, name, canonical_name, remove=(7, 0))
    return deprecated_object


class document(nodes.document):
    """The document root element patched by Sphinx.

    This fixes that document.set_id() does not support a node having multiple node Ids.
    see https://sourceforge.net/p/docutils/patches/167/

    .. important:: This is only for Sphinx internal use.  Please don't use this
                   in your extensions.  It will be removed without deprecation period.
    """

    def set_id(self, node: Element, msgnode: Element | None = None,
               suggested_prefix: str = '') -> str:
        return super().set_id(node, msgnode, suggested_prefix)  # type: ignore[call-arg]


class translatable(nodes.Node):
    """Node which supports translation.

    The translation goes forward with following steps:

    1. Preserve original translatable messages
    2. Apply translated messages from message catalog
    3. Extract preserved messages (for gettext builder)

    The translatable nodes MUST preserve original messages.
    And these messages should not be overridden at applying step.
    Because they are used at final step; extraction.
    """

    def preserve_original_messages(self) -> None:
        """Preserve original translatable messages."""
        raise NotImplementedError

    def apply_translated_message(self, original_message: str, translated_message: str) -> None:
        """Apply translated message."""
        raise NotImplementedError

    def extract_original_messages(self) -> Sequence[str]:
        """Extract translation messages.

        :returns: list of extracted messages or messages generator
        """
        raise NotImplementedError


class not_smartquotable:
    """A node which does not support smart-quotes."""
    support_smartquotes = False


class toctree(nodes.General, nodes.Element, translatable):
    """Node for inserting a "TOC tree"."""

    def preserve_original_messages(self) -> None:
        # toctree entries
        rawentries = self.setdefault('rawentries', [])
        for title, _docname in self['entries']:
            if title:
                rawentries.append(title)

        # :caption: option
        if self.get('caption'):
            self['rawcaption'] = self['caption']

    def apply_translated_message(self, original_message: str, translated_message: str) -> None:
        # toctree entries
        for i, (title, docname) in enumerate(self['entries']):
            if title == original_message:
                self['entries'][i] = (translated_message, docname)

        # :caption: option
        if self.get('rawcaption') == original_message:
            self['caption'] = translated_message

    def extract_original_messages(self) -> list[str]:
        messages: list[str] = []

        # toctree entries
        messages.extend(self.get('rawentries', []))

        # :caption: option
        if 'rawcaption' in self:
            messages.append(self['rawcaption'])
        return messages


#############################################################
# Domain-specific object descriptions (class, function etc.)
#############################################################

class _desc_classes_injector(nodes.Element, not_smartquotable):
    """Helper base class for injecting a fixed list of classes.

    Use as the first base class.
    """

    classes: list[str] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self['classes'].extend(self.classes)


# Top-level nodes
#################

class desc(nodes.Admonition, nodes.Element):
    """Node for a list of object signatures and a common description of them.

    Contains one or more :py:class:`desc_signature` nodes
    and then a single :py:class:`desc_content` node.

    This node always has two classes:

    - The name of the domain it belongs to, e.g., ``py`` or ``cpp``.
    - The name of the object type in the domain, e.g., ``function``.
    """

    # TODO: can we introduce a constructor
    #  that forces the specification of the domain and objtyp?


class desc_signature(_desc_classes_injector, nodes.Part, nodes.Inline, nodes.TextElement):
    """Node for a single object signature.

    As default the signature is a single-line signature.
    Set ``is_multiline = True`` to describe a multi-line signature.
    In that case all child nodes must be :py:class:`desc_signature_line` nodes.

    This node always has the classes ``sig``, ``sig-object``, and the domain it belongs to.
    """
    # Note: the domain name is being added through a post-transform DescSigAddDomainAsClass
    classes = ['sig', 'sig-object']

    @property
    def child_text_separator(self):
        if self.get('is_multiline'):
            return ' '
        else:
            return super().child_text_separator


class desc_signature_line(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a line in a multi-line object signature.

    It should only be used as a child of a :py:class:`desc_signature`
    with ``is_multiline`` set to ``True``.
    Set ``add_permalink = True`` for the line that should get the permalink.
    """
    sphinx_line_type = ''


class desc_content(nodes.General, nodes.Element):
    """Node for object description content.

    Must be the last child node in a :py:class:`desc` node.
    """


class desc_inline(_desc_classes_injector, nodes.Inline, nodes.TextElement):
    """Node for a signature fragment in inline text.

    This is for example used for roles like :rst:role:`cpp:expr`.

    This node always has the classes ``sig``, ``sig-inline``,
    and the name of the domain it belongs to.
    """
    classes = ['sig', 'sig-inline']

    def __init__(self, domain: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs, domain=domain)
        self['classes'].append(domain)


# Nodes for high-level structure in signatures
##############################################

# nodes to use within a desc_signature or desc_signature_line

class desc_name(_desc_classes_injector, nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for the main object name.

    For example, in the declaration of a Python class ``MyModule.MyClass``,
    the main name is ``MyClass``.

    This node always has the class ``sig-name``.
    """
    classes = ['sig-name', 'descname']  # 'descname' is for backwards compatibility


class desc_addname(_desc_classes_injector, nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for additional name parts for an object.

    For example, in the declaration of a Python class ``MyModule.MyClass``,
    the additional name part is ``MyModule.``.

    This node always has the class ``sig-prename``.
    """
    # 'descclassname' is for backwards compatibility
    classes = ['sig-prename', 'descclassname']


# compatibility alias
desc_classname = desc_addname


class desc_type(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for return types or object type names."""


class desc_returns(desc_type):
    """Node for a "returns" annotation (a la -> in Python)."""

    def astext(self) -> str:
        return ' -> ' + super().astext()


class desc_parameterlist(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a general parameter list.

    As default the parameter list is written in line with the rest of the signature.
    Set ``multi_line_parameter_list = True`` to describe a multi-line parameter list.
    In that case each parameter will then be written on its own, indented line.
    """
    child_text_separator = ', '

    def astext(self):
        return f'({super().astext()})'


class desc_type_parameter_list(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a general type parameter list.

    As default the type parameters list is written in line with the rest of the signature.
    Set ``multi_line_parameter_list = True`` to describe a multi-line type parameters list.
    In that case each type parameter will then be written on its own, indented line.
    """
    child_text_separator = ', '

    def astext(self):
        return f'[{super().astext()}]'


class desc_parameter(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a single parameter."""


class desc_type_parameter(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a single type parameter."""


class desc_optional(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for marking optional parts of the parameter list."""
    child_text_separator = ', '

    def astext(self) -> str:
        return '[' + super().astext() + ']'


class desc_annotation(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for signature annotations (not Python 3-style annotations)."""


# Leaf nodes for markup of text fragments
#########################################

#: A set of classes inheriting :class:`desc_sig_element`. Each node class
#: is expected to be handled by the builder's translator class if the latter
#: does not inherit from SphinxTranslator.
#:
#: This set can be extended manually by third-party extensions or
#: by subclassing :class:`desc_sig_element` and using the class
#: keyword argument `_sig_element=True`.
SIG_ELEMENTS: set[type[desc_sig_element]] = set()


# Signature text elements, generally translated to node.inline
# in SigElementFallbackTransform.
# When adding a new one, add it to SIG_ELEMENTS via the class
# keyword argument `_sig_element=True` (e.g., see `desc_sig_space`).

class desc_sig_element(nodes.inline, _desc_classes_injector):
    """Common parent class of nodes for inline text of a signature."""
    classes: list[str] = []

    def __init__(self, rawsource: str = '', text: str = '',
                 *children: Element, **attributes: Any) -> None:
        super().__init__(rawsource, text, *children, **attributes)
        self['classes'].extend(self.classes)

    def __init_subclass__(cls, *, _sig_element=False, **kwargs):
        super().__init_subclass__(**kwargs)
        if _sig_element:
            # add the class to the SIG_ELEMENTS set if asked
            SIG_ELEMENTS.add(cls)


# to not reinvent the wheel, the classes in the following desc_sig classes
# are based on those used in Pygments

class desc_sig_space(desc_sig_element, _sig_element=True):
    """Node for a space in a signature."""
    classes = ["w"]

    def __init__(self, rawsource: str = '', text: str = ' ',
                 *children: Element, **attributes: Any) -> None:
        super().__init__(rawsource, text, *children, **attributes)


class desc_sig_name(desc_sig_element, _sig_element=True):
    """Node for an identifier in a signature."""
    classes = ["n"]


class desc_sig_operator(desc_sig_element, _sig_element=True):
    """Node for an operator in a signature."""
    classes = ["o"]


class desc_sig_punctuation(desc_sig_element, _sig_element=True):
    """Node for punctuation in a signature."""
    classes = ["p"]


class desc_sig_keyword(desc_sig_element, _sig_element=True):
    """Node for a general keyword in a signature."""
    classes = ["k"]


class desc_sig_keyword_type(desc_sig_element, _sig_element=True):
    """Node for a keyword which is a built-in type in a signature."""
    classes = ["kt"]


class desc_sig_literal_number(desc_sig_element, _sig_element=True):
    """Node for a numeric literal in a signature."""
    classes = ["m"]


class desc_sig_literal_string(desc_sig_element, _sig_element=True):
    """Node for a string literal in a signature."""
    classes = ["s"]


class desc_sig_literal_char(desc_sig_element, _sig_element=True):
    """Node for a character literal in a signature."""
    classes = ["sc"]


###############################################################
# new admonition-like constructs

class versionmodified(nodes.Admonition, nodes.TextElement):
    """Node for version change entries.

    Currently used for "versionadded", "versionchanged" and "deprecated"
    directives.
    """


class seealso(nodes.Admonition, nodes.Element):
    """Custom "see also" admonition."""


class productionlist(nodes.Admonition, nodes.Element):
    """Node for grammar production lists.

    Contains ``production`` nodes.
    """


class production(nodes.Part, nodes.Inline, nodes.FixedTextElement):
    """Node for a single grammar production rule."""


# other directive-level nodes

class index(nodes.Invisible, nodes.Inline, nodes.TextElement):
    """Node for index entries.

    This node is created by the ``index`` directive and has one attribute,
    ``entries``.  Its value is a list of 5-tuples of ``(entrytype, entryname,
    target, ignored, key)``.

    *entrytype* is one of "single", "pair", "double", "triple".

    *key* is categorization characters (usually a single character) for
    general index page. For the details of this, please see also:
    :rst:dir:`glossary` and issue #2320.
    """


class centered(nodes.Part, nodes.TextElement):
    """This node is deprecated."""


class acks(nodes.Element):
    """Special node for "acks" lists."""


class hlist(nodes.Element):
    """Node for "horizontal lists", i.e. lists that should be compressed to
    take up less vertical space.
    """


class hlistcol(nodes.Element):
    """Node for one column in a horizontal list."""


class compact_paragraph(nodes.paragraph):
    """Node for a compact paragraph (which never makes a <p> node)."""


class glossary(nodes.Element):
    """Node to insert a glossary."""


class only(nodes.Element):
    """Node for "only" directives (conditional inclusion based on tags)."""


# meta-information nodes

class start_of_file(nodes.Element):
    """Node to mark start of a new file, used in the LaTeX builder only."""


class highlightlang(nodes.Element):
    """Inserted to set the highlight language and line number options for
    subsequent code blocks.
    """


class tabular_col_spec(nodes.Element):
    """Node for specifying tabular columns, used for LaTeX output."""


# inline nodes

class pending_xref(nodes.Inline, nodes.Element):
    """Node for cross-references that cannot be resolved without complete
    information about all documents.

    These nodes are resolved before writing output, in
    BuildEnvironment.resolve_references.
    """
    child_text_separator = ''


class pending_xref_condition(nodes.Inline, nodes.TextElement):
    """Node representing a potential way to create a cross-reference and the
    condition in which this way should be used.

    This node is only allowed to be placed under a :py:class:`pending_xref`
    node.  A **pending_xref** node must contain either no **pending_xref_condition**
    nodes or it must only contains **pending_xref_condition** nodes.

    The cross-reference resolver will replace a :py:class:`pending_xref` which
    contains **pending_xref_condition** nodes by the content of exactly one of
    those **pending_xref_condition** nodes' content. It uses the **condition**
    attribute to decide which **pending_xref_condition** node's content to
    use. For example, let us consider how the cross-reference resolver acts on::

        <pending_xref refdomain="py" reftarget="io.StringIO ...>
            <pending_xref_condition condition="resolved">
                <literal>
                    StringIO
            <pending_xref_condition condition="*">
                <literal>
                    io.StringIO

    If the cross-reference resolver successfully resolves the cross-reference,
    then it rewrites the **pending_xref** as::

        <reference>
            <literal>
                StringIO

    Otherwise, if the cross-reference resolution failed, it rewrites the
    **pending_xref** as::

        <reference>
            <literal>
                io.StringIO

    The **pending_xref_condition** node should have **condition** attribute.
    Domains can be store their individual conditions into the attribute to
    filter contents on resolving phase.  As a reserved condition name,
    ``condition="*"`` is used for the fallback of resolution failure.
    Additionally, as a recommended condition name, ``condition="resolved"``
    represents a resolution success in the intersphinx module.

    .. versionadded:: 4.0
    """


class number_reference(nodes.reference):
    """Node for number references, similar to pending_xref."""


class download_reference(nodes.reference):
    """Node for download references, similar to pending_xref."""


class literal_emphasis(nodes.emphasis, not_smartquotable):
    """Node that behaves like `emphasis`, but further text processors are not
    applied (e.g. smartypants for HTML output).
    """


class literal_strong(nodes.strong, not_smartquotable):
    """Node that behaves like `strong`, but further text processors are not
    applied (e.g. smartypants for HTML output).
    """


class manpage(nodes.Inline, nodes.FixedTextElement):
    """Node for references to manpages."""


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_node(toctree)

    app.add_node(desc)
    app.add_node(desc_signature)
    app.add_node(desc_signature_line)
    app.add_node(desc_content)
    app.add_node(desc_inline)

    app.add_node(desc_name)
    app.add_node(desc_addname)
    app.add_node(desc_type)
    app.add_node(desc_returns)
    app.add_node(desc_parameterlist)
    app.add_node(desc_type_parameter_list)
    app.add_node(desc_parameter)
    app.add_node(desc_type_parameter)
    app.add_node(desc_optional)
    app.add_node(desc_annotation)

    for n in SIG_ELEMENTS:
        app.add_node(n)

    app.add_node(versionmodified)
    app.add_node(seealso)
    app.add_node(productionlist)
    app.add_node(production)
    app.add_node(index)
    app.add_node(centered)
    app.add_node(acks)
    app.add_node(hlist)
    app.add_node(hlistcol)
    app.add_node(compact_paragraph)
    app.add_node(glossary)
    app.add_node(only)
    app.add_node(start_of_file)
    app.add_node(highlightlang)
    app.add_node(tabular_col_spec)
    app.add_node(pending_xref)
    app.add_node(number_reference)
    app.add_node(download_reference)
    app.add_node(literal_emphasis)
    app.add_node(literal_strong)
    app.add_node(manpage)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
