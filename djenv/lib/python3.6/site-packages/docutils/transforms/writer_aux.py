# $Id: writer_aux.py 7808 2015-02-27 17:03:32Z milde $
# Author: Lea Wiemann <LeWiemann@gmail.com>
# Copyright: This module has been placed in the public domain.

"""
Auxiliary transforms mainly to be used by Writer components.

This module is called "writer_aux" because otherwise there would be
conflicting imports like this one::

    from docutils import writers
    from docutils.transforms import writers
"""

__docformat__ = 'reStructuredText'

from docutils import nodes, utils, languages
from docutils.transforms import Transform


class Compound(Transform):

    """
    Flatten all compound paragraphs.  For example, transform ::

        <compound>
            <paragraph>
            <literal_block>
            <paragraph>

    into ::

        <paragraph>
        <literal_block classes="continued">
        <paragraph classes="continued">
    """

    default_priority = 910

    def apply(self):
        for compound in self.document.traverse(nodes.compound):
            first_child = True
            for child in compound:
                if first_child:
                    if not isinstance(child, nodes.Invisible):
                        first_child = False
                else:
                    child['classes'].append('continued')
            # Substitute children for compound.
            compound.replace_self(compound[:])


class Admonitions(Transform):

    """
    Transform specific admonitions, like this:

        <note>
            <paragraph>
                 Note contents ...

    into generic admonitions, like this::

        <admonition classes="note">
            <title>
                Note
            <paragraph>
                Note contents ...

    The admonition title is localized.
    """

    default_priority = 920

    def apply(self):
        language = languages.get_language(self.document.settings.language_code,
                                          self.document.reporter)
        for node in self.document.traverse(nodes.Admonition):
            node_name = node.__class__.__name__
            # Set class, so that we know what node this admonition came from.
            node['classes'].append(node_name)
            if not isinstance(node, nodes.admonition):
                # Specific admonition.  Transform into a generic admonition.
                admonition = nodes.admonition(node.rawsource, *node.children,
                                              **node.attributes)
                title = nodes.title('', language.labels[node_name])
                admonition.insert(0, title)
                node.replace_self(admonition)
