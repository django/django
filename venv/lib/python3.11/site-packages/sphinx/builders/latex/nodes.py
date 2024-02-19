"""Additional nodes for LaTeX writer."""

from docutils import nodes


class captioned_literal_block(nodes.container):
    """A node for a container of literal_block having a caption."""
    pass


class footnotemark(nodes.Inline, nodes.Referential, nodes.TextElement):
    """A node represents ``\footnotemark``."""
    pass


class footnotetext(nodes.General, nodes.BackLinkable, nodes.Element,
                   nodes.Labeled, nodes.Targetable):
    """A node represents ``\footnotetext``."""


class math_reference(nodes.Inline, nodes.Referential, nodes.TextElement):
    """A node for a reference for equation."""
    pass


class thebibliography(nodes.container):
    """A node for wrapping bibliographies."""
    pass


HYPERLINK_SUPPORT_NODES = (
    nodes.figure,
    nodes.literal_block,
    nodes.table,
    nodes.section,
    captioned_literal_block,
)
