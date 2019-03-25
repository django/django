# -*- coding: utf-8 -*-
"""
    sphinx.environment.adapters.toctree
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Toctree adapter for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from six import iteritems

from sphinx import addnodes
from sphinx.locale import __
from sphinx.util import url_re, logging
from sphinx.util.matching import Matcher
from sphinx.util.nodes import clean_astext, process_only_nodes

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


class TocTree(object):
    def __init__(self, env):
        # type: (BuildEnvironment) -> None
        self.env = env

    def note(self, docname, toctreenode):
        # type: (unicode, addnodes.toctree) -> None
        """Note a TOC tree directive in a document and gather information about
        file relations from it.
        """
        if toctreenode['glob']:
            self.env.glob_toctrees.add(docname)
        if toctreenode.get('numbered'):
            self.env.numbered_toctrees.add(docname)
        includefiles = toctreenode['includefiles']
        for includefile in includefiles:
            # note that if the included file is rebuilt, this one must be
            # too (since the TOC of the included file could have changed)
            self.env.files_to_rebuild.setdefault(includefile, set()).add(docname)
        self.env.toctree_includes.setdefault(docname, []).extend(includefiles)

    def resolve(self, docname, builder, toctree, prune=True, maxdepth=0,
                titles_only=False, collapse=False, includehidden=False):
        # type: (unicode, Builder, addnodes.toctree, bool, int, bool, bool, bool) -> nodes.Node
        """Resolve a *toctree* node into individual bullet lists with titles
        as items, returning None (if no containing titles are found) or
        a new node.

        If *prune* is True, the tree is pruned to *maxdepth*, or if that is 0,
        to the value of the *maxdepth* option on the *toctree* node.
        If *titles_only* is True, only toplevel document titles will be in the
        resulting tree.
        If *collapse* is True, all branches not containing docname will
        be collapsed.
        """
        if toctree.get('hidden', False) and not includehidden:
            return None

        # For reading the following two helper function, it is useful to keep
        # in mind the node structure of a toctree (using HTML-like node names
        # for brevity):
        #
        # <ul>
        #   <li>
        #     <p><a></p>
        #     <p><a></p>
        #     ...
        #     <ul>
        #       ...
        #     </ul>
        #   </li>
        # </ul>
        #
        # The transformation is made in two passes in order to avoid
        # interactions between marking and pruning the tree (see bug #1046).

        toctree_ancestors = self.get_toctree_ancestors(docname)
        excluded = Matcher(self.env.config.exclude_patterns)

        def _toctree_add_classes(node, depth):
            # type: (nodes.Node, int) -> None
            """Add 'toctree-l%d' and 'current' classes to the toctree."""
            for subnode in node.children:
                if isinstance(subnode, (addnodes.compact_paragraph,
                                        nodes.list_item)):
                    # for <p> and <li>, indicate the depth level and recurse
                    subnode['classes'].append('toctree-l%d' % (depth - 1))
                    _toctree_add_classes(subnode, depth)
                elif isinstance(subnode, nodes.bullet_list):
                    # for <ul>, just recurse
                    _toctree_add_classes(subnode, depth + 1)
                elif isinstance(subnode, nodes.reference):
                    # for <a>, identify which entries point to the current
                    # document and therefore may not be collapsed
                    if subnode['refuri'] == docname:
                        if not subnode['anchorname']:
                            # give the whole branch a 'current' class
                            # (useful for styling it differently)
                            branchnode = subnode
                            while branchnode:
                                branchnode['classes'].append('current')
                                branchnode = branchnode.parent
                        # mark the list_item as "on current page"
                        if subnode.parent.parent.get('iscurrent'):
                            # but only if it's not already done
                            return
                        while subnode:
                            subnode['iscurrent'] = True
                            subnode = subnode.parent

        def _entries_from_toctree(toctreenode, parents, separate=False, subtree=False):
            # type: (addnodes.toctree, List[nodes.Node], bool, bool) -> List[nodes.Node]
            """Return TOC entries for a toctree node."""
            refs = [(e[0], e[1]) for e in toctreenode['entries']]
            entries = []
            for (title, ref) in refs:
                try:
                    refdoc = None
                    if url_re.match(ref):
                        if title is None:
                            title = ref
                        reference = nodes.reference('', '', internal=False,
                                                    refuri=ref, anchorname='',
                                                    *[nodes.Text(title)])
                        para = addnodes.compact_paragraph('', '', reference)
                        item = nodes.list_item('', para)
                        toc = nodes.bullet_list('', item)
                    elif ref == 'self':
                        # 'self' refers to the document from which this
                        # toctree originates
                        ref = toctreenode['parent']
                        if not title:
                            title = clean_astext(self.env.titles[ref])
                        reference = nodes.reference('', '', internal=True,
                                                    refuri=ref,
                                                    anchorname='',
                                                    *[nodes.Text(title)])
                        para = addnodes.compact_paragraph('', '', reference)
                        item = nodes.list_item('', para)
                        # don't show subitems
                        toc = nodes.bullet_list('', item)
                    else:
                        if ref in parents:
                            logger.warning(__('circular toctree references '
                                              'detected, ignoring: %s <- %s'),
                                           ref, ' <- '.join(parents),
                                           location=ref)
                            continue
                        refdoc = ref
                        toc = self.env.tocs[ref].deepcopy()
                        maxdepth = self.env.metadata[ref].get('tocdepth', 0)
                        if ref not in toctree_ancestors or (prune and maxdepth > 0):
                            self._toctree_prune(toc, 2, maxdepth, collapse)
                        process_only_nodes(toc, builder.tags)
                        if title and toc.children and len(toc.children) == 1:
                            child = toc.children[0]
                            for refnode in child.traverse(nodes.reference):
                                if refnode['refuri'] == ref and \
                                   not refnode['anchorname']:
                                    refnode.children = [nodes.Text(title)]
                    if not toc.children:
                        # empty toc means: no titles will show up in the toctree
                        logger.warning(__('toctree contains reference to document %r that '
                                          'doesn\'t have a title: no link will be generated'),
                                       ref, location=toctreenode)
                except KeyError:
                    # this is raised if the included file does not exist
                    if excluded(self.env.doc2path(ref, None)):
                        message = __('toctree contains reference to excluded document %r')
                    else:
                        message = __('toctree contains reference to nonexisting document %r')

                    logger.warning(message, ref, location=toctreenode)
                else:
                    # if titles_only is given, only keep the main title and
                    # sub-toctrees
                    if titles_only:
                        # delete everything but the toplevel title(s)
                        # and toctrees
                        for toplevel in toc:
                            # nodes with length 1 don't have any children anyway
                            if len(toplevel) > 1:
                                subtrees = toplevel.traverse(addnodes.toctree)
                                if subtrees:
                                    toplevel[1][:] = subtrees
                                else:
                                    toplevel.pop(1)
                    # resolve all sub-toctrees
                    for subtocnode in toc.traverse(addnodes.toctree):
                        if not (subtocnode.get('hidden', False) and
                                not includehidden):
                            i = subtocnode.parent.index(subtocnode) + 1
                            for item in _entries_from_toctree(
                                    subtocnode, [refdoc] + parents,
                                    subtree=True):
                                subtocnode.parent.insert(i, item)
                                i += 1
                            subtocnode.parent.remove(subtocnode)
                    if separate:
                        entries.append(toc)
                    else:
                        entries.extend(toc.children)
            if not subtree and not separate:
                ret = nodes.bullet_list()
                ret += entries
                return [ret]
            return entries

        maxdepth = maxdepth or toctree.get('maxdepth', -1)
        if not titles_only and toctree.get('titlesonly', False):
            titles_only = True
        if not includehidden and toctree.get('includehidden', False):
            includehidden = True

        # NOTE: previously, this was separate=True, but that leads to artificial
        # separation when two or more toctree entries form a logical unit, so
        # separating mode is no longer used -- it's kept here for history's sake
        tocentries = _entries_from_toctree(toctree, [], separate=False)
        if not tocentries:
            return None

        newnode = addnodes.compact_paragraph('', '')
        caption = toctree.attributes.get('caption')
        if caption:
            caption_node = nodes.caption(caption, '', *[nodes.Text(caption)])
            caption_node.line = toctree.line
            caption_node.source = toctree.source
            caption_node.rawsource = toctree['rawcaption']
            if hasattr(toctree, 'uid'):
                # move uid to caption_node to translate it
                caption_node.uid = toctree.uid
                del toctree.uid
            newnode += caption_node
        newnode.extend(tocentries)
        newnode['toctree'] = True

        # prune the tree to maxdepth, also set toc depth and current classes
        _toctree_add_classes(newnode, 1)
        self._toctree_prune(newnode, 1, prune and maxdepth or 0, collapse)

        if len(newnode[-1]) == 0:  # No titles found
            return None

        # set the target paths in the toctrees (they are not known at TOC
        # generation time)
        for refnode in newnode.traverse(nodes.reference):
            if not url_re.match(refnode['refuri']):
                refnode['refuri'] = builder.get_relative_uri(
                    docname, refnode['refuri']) + refnode['anchorname']
        return newnode

    def get_toctree_ancestors(self, docname):
        # type: (unicode) -> List[unicode]
        parent = {}
        for p, children in iteritems(self.env.toctree_includes):
            for child in children:
                parent[child] = p
        ancestors = []  # type: List[unicode]
        d = docname
        while d in parent and d not in ancestors:
            ancestors.append(d)
            d = parent[d]
        return ancestors

    def _toctree_prune(self, node, depth, maxdepth, collapse=False):
        # type: (nodes.Node, int, int, bool) -> None
        """Utility: Cut a TOC at a specified depth."""
        for subnode in node.children[:]:
            if isinstance(subnode, (addnodes.compact_paragraph,
                                    nodes.list_item)):
                # for <p> and <li>, just recurse
                self._toctree_prune(subnode, depth, maxdepth, collapse)
            elif isinstance(subnode, nodes.bullet_list):
                # for <ul>, determine if the depth is too large or if the
                # entry is to be collapsed
                if maxdepth > 0 and depth > maxdepth:
                    subnode.parent.replace(subnode, [])
                else:
                    # cull sub-entries whose parents aren't 'current'
                    if (collapse and depth > 1 and
                            'iscurrent' not in subnode.parent):
                        subnode.parent.remove(subnode)
                    else:
                        # recurse on visible children
                        self._toctree_prune(subnode, depth + 1, maxdepth,  collapse)

    def get_toc_for(self, docname, builder):
        # type: (unicode, Builder) -> Dict[unicode, nodes.Node]
        """Return a TOC nodetree -- for use on the same page only!"""
        tocdepth = self.env.metadata[docname].get('tocdepth', 0)
        try:
            toc = self.env.tocs[docname].deepcopy()
            self._toctree_prune(toc, 2, tocdepth)
        except KeyError:
            # the document does not exist anymore: return a dummy node that
            # renders to nothing
            return nodes.paragraph()
        process_only_nodes(toc, builder.tags)
        for node in toc.traverse(nodes.reference):
            node['refuri'] = node['anchorname'] or '#'
        return toc

    def get_toctree_for(self, docname, builder, collapse, **kwds):
        # type: (unicode, Builder, bool, Any) -> nodes.Node
        """Return the global TOC nodetree."""
        doctree = self.env.get_doctree(self.env.config.master_doc)
        toctrees = []
        if 'includehidden' not in kwds:
            kwds['includehidden'] = True
        if 'maxdepth' not in kwds:
            kwds['maxdepth'] = 0
        kwds['collapse'] = collapse
        for toctreenode in doctree.traverse(addnodes.toctree):
            toctree = self.resolve(docname, builder, toctreenode, prune=True, **kwds)
            if toctree:
                toctrees.append(toctree)
        if not toctrees:
            return None
        result = toctrees[0]
        for toctree in toctrees[1:]:
            result.extend(toctree.children)
        return result
