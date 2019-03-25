# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors.toctree
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Toctree collector for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from six import iteritems

from sphinx import addnodes
from sphinx.environment.adapters.toctree import TocTree
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.locale import __
from sphinx.transforms import SphinxContentsFilter
from sphinx.util import url_re, logging

if False:
    # For type annotation
    from typing import Any, Dict, List, Set, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


class TocTreeCollector(EnvironmentCollector):
    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.tocs.pop(docname, None)
        env.toc_secnumbers.pop(docname, None)
        env.toc_fignumbers.pop(docname, None)
        env.toc_num_entries.pop(docname, None)
        env.toctree_includes.pop(docname, None)
        env.glob_toctrees.discard(docname)
        env.numbered_toctrees.discard(docname)

        for subfn, fnset in list(env.files_to_rebuild.items()):
            fnset.discard(docname)
            if not fnset:
                del env.files_to_rebuild[subfn]

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        for docname in docnames:
            env.tocs[docname] = other.tocs[docname]
            env.toc_num_entries[docname] = other.toc_num_entries[docname]
            if docname in other.toctree_includes:
                env.toctree_includes[docname] = other.toctree_includes[docname]
            if docname in other.glob_toctrees:
                env.glob_toctrees.add(docname)
            if docname in other.numbered_toctrees:
                env.numbered_toctrees.add(docname)

        for subfn, fnset in other.files_to_rebuild.items():
            env.files_to_rebuild.setdefault(subfn, set()).update(fnset & set(docnames))

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Build a TOC from the doctree and store it in the inventory."""
        docname = app.env.docname
        numentries = [0]  # nonlocal again...

        def traverse_in_section(node, cls):
            # type: (nodes.Node, Any) -> List[nodes.Node]
            """Like traverse(), but stay within the same section."""
            result = []
            if isinstance(node, cls):
                result.append(node)
            for child in node.children:
                if isinstance(child, nodes.section):
                    continue
                result.extend(traverse_in_section(child, cls))
            return result

        def build_toc(node, depth=1):
            # type: (nodes.Node, int) -> List[nodes.Node]
            entries = []
            for sectionnode in node:
                # find all toctree nodes in this section and add them
                # to the toc (just copying the toctree node which is then
                # resolved in self.get_and_resolve_doctree)
                if isinstance(sectionnode, addnodes.only):
                    onlynode = addnodes.only(expr=sectionnode['expr'])
                    blist = build_toc(sectionnode, depth)
                    if blist:
                        onlynode += blist.children  # type: ignore
                        entries.append(onlynode)
                    continue
                if not isinstance(sectionnode, nodes.section):
                    for toctreenode in traverse_in_section(sectionnode,
                                                           addnodes.toctree):
                        item = toctreenode.copy()
                        entries.append(item)
                        # important: do the inventory stuff
                        TocTree(app.env).note(docname, toctreenode)
                    continue
                title = sectionnode[0]
                # copy the contents of the section title, but without references
                # and unnecessary stuff
                visitor = SphinxContentsFilter(doctree)
                title.walkabout(visitor)
                nodetext = visitor.get_entry_text()
                if not numentries[0]:
                    # for the very first toc entry, don't add an anchor
                    # as it is the file's title anyway
                    anchorname = ''
                else:
                    anchorname = '#' + sectionnode['ids'][0]
                numentries[0] += 1
                # make these nodes:
                # list_item -> compact_paragraph -> reference
                reference = nodes.reference(
                    '', '', internal=True, refuri=docname,
                    anchorname=anchorname, *nodetext)
                para = addnodes.compact_paragraph('', '', reference)
                item = nodes.list_item('', para)
                sub_item = build_toc(sectionnode, depth + 1)
                item += sub_item
                entries.append(item)
            if entries:
                return nodes.bullet_list('', *entries)
            return []
        toc = build_toc(doctree)
        if toc:
            app.env.tocs[docname] = toc
        else:
            app.env.tocs[docname] = nodes.bullet_list('')
        app.env.toc_num_entries[docname] = numentries[0]

    def get_updated_docs(self, app, env):
        # type: (Sphinx, BuildEnvironment) -> List[unicode]
        return self.assign_section_numbers(env) + self.assign_figure_numbers(env)

    def assign_section_numbers(self, env):
        # type: (BuildEnvironment) -> List[unicode]
        """Assign a section number to each heading under a numbered toctree."""
        # a list of all docnames whose section numbers changed
        rewrite_needed = []

        assigned = set()  # type: Set[unicode]
        old_secnumbers = env.toc_secnumbers
        env.toc_secnumbers = {}

        def _walk_toc(node, secnums, depth, titlenode=None):
            # type: (nodes.Node, Dict, int, nodes.Node) -> None
            # titlenode is the title of the document, it will get assigned a
            # secnumber too, so that it shows up in next/prev/parent rellinks
            for subnode in node.children:
                if isinstance(subnode, nodes.bullet_list):
                    numstack.append(0)
                    _walk_toc(subnode, secnums, depth - 1, titlenode)
                    numstack.pop()
                    titlenode = None
                elif isinstance(subnode, nodes.list_item):
                    _walk_toc(subnode, secnums, depth, titlenode)
                    titlenode = None
                elif isinstance(subnode, addnodes.only):
                    # at this stage we don't know yet which sections are going
                    # to be included; just include all of them, even if it leads
                    # to gaps in the numbering
                    _walk_toc(subnode, secnums, depth, titlenode)
                    titlenode = None
                elif isinstance(subnode, addnodes.compact_paragraph):
                    numstack[-1] += 1
                    if depth > 0:
                        number = list(numstack)
                        secnums[subnode[0]['anchorname']] = tuple(numstack)
                    else:
                        number = None
                        secnums[subnode[0]['anchorname']] = None
                    subnode[0]['secnumber'] = number
                    if titlenode:
                        titlenode['secnumber'] = number
                        titlenode = None
                elif isinstance(subnode, addnodes.toctree):
                    _walk_toctree(subnode, depth)

        def _walk_toctree(toctreenode, depth):
            # type: (nodes.Node, int) -> None
            if depth == 0:
                return
            for (title, ref) in toctreenode['entries']:
                if url_re.match(ref) or ref == 'self':
                    # don't mess with those
                    continue
                elif ref in assigned:
                    logger.warning(__('%s is already assigned section numbers '
                                      '(nested numbered toctree?)'), ref,
                                   location=toctreenode, type='toc', subtype='secnum')
                elif ref in env.tocs:
                    secnums = env.toc_secnumbers[ref] = {}
                    assigned.add(ref)
                    _walk_toc(env.tocs[ref], secnums, depth,
                              env.titles.get(ref))
                    if secnums != old_secnumbers.get(ref):
                        rewrite_needed.append(ref)

        for docname in env.numbered_toctrees:
            assigned.add(docname)
            doctree = env.get_doctree(docname)
            for toctreenode in doctree.traverse(addnodes.toctree):
                depth = toctreenode.get('numbered', 0)
                if depth:
                    # every numbered toctree gets new numbering
                    numstack = [0]
                    _walk_toctree(toctreenode, depth)

        return rewrite_needed

    def assign_figure_numbers(self, env):
        # type: (BuildEnvironment) -> List[unicode]
        """Assign a figure number to each figure under a numbered toctree."""

        rewrite_needed = []

        assigned = set()  # type: Set[unicode]
        old_fignumbers = env.toc_fignumbers
        env.toc_fignumbers = {}
        fignum_counter = {}  # type: Dict[unicode, Dict[Tuple[int, ...], int]]

        def get_figtype(node):
            # type: (nodes.Node) -> unicode
            for domain in env.domains.values():
                figtype = domain.get_enumerable_node_type(node)
                if figtype:
                    return figtype

            return None

        def get_section_number(docname, section):
            # type: (unicode, nodes.Node) -> Tuple[int, ...]
            anchorname = '#' + section['ids'][0]
            secnumbers = env.toc_secnumbers.get(docname, {})
            if anchorname in secnumbers:
                secnum = secnumbers.get(anchorname)
            else:
                secnum = secnumbers.get('')

            return secnum or tuple()

        def get_next_fignumber(figtype, secnum):
            # type: (unicode, Tuple[int, ...]) -> Tuple[int, ...]
            counter = fignum_counter.setdefault(figtype, {})

            secnum = secnum[:env.config.numfig_secnum_depth]
            counter[secnum] = counter.get(secnum, 0) + 1
            return secnum + (counter[secnum],)

        def register_fignumber(docname, secnum, figtype, fignode):
            # type: (unicode, Tuple[int], unicode, nodes.Node) -> None
            env.toc_fignumbers.setdefault(docname, {})
            fignumbers = env.toc_fignumbers[docname].setdefault(figtype, {})
            figure_id = fignode['ids'][0]

            fignumbers[figure_id] = get_next_fignumber(figtype, secnum)

        def _walk_doctree(docname, doctree, secnum):
            # type: (unicode, nodes.Node, Tuple[int, ...]) -> None
            for subnode in doctree.children:
                if isinstance(subnode, nodes.section):
                    next_secnum = get_section_number(docname, subnode)
                    if next_secnum:
                        _walk_doctree(docname, subnode, next_secnum)
                    else:
                        _walk_doctree(docname, subnode, secnum)
                    continue
                elif isinstance(subnode, addnodes.toctree):
                    for title, subdocname in subnode['entries']:
                        if url_re.match(subdocname) or subdocname == 'self':
                            # don't mess with those
                            continue

                        _walk_doc(subdocname, secnum)

                    continue

                figtype = get_figtype(subnode)
                if figtype and subnode['ids']:
                    register_fignumber(docname, secnum, figtype, subnode)

                _walk_doctree(docname, subnode, secnum)

        def _walk_doc(docname, secnum):
            # type: (unicode, Tuple[int]) -> None
            if docname not in assigned:
                assigned.add(docname)
                doctree = env.get_doctree(docname)
                _walk_doctree(docname, doctree, secnum)

        if env.config.numfig:
            _walk_doc(env.config.master_doc, tuple())  # type: ignore
            for docname, fignums in iteritems(env.toc_fignumbers):
                if fignums != old_fignumbers.get(docname):
                    rewrite_needed.append(docname)

        return rewrite_needed


def setup(app):
    # type: (Sphinx) -> Dict
    app.add_env_collector(TocTreeCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
