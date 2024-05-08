# $Id: frontmatter.py 9552 2024-03-08 23:41:31Z milde $
# Author: David Goodger, Ueli Schlaepfer <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Transforms_ related to the front matter of a document or a section
(information found before the main text):

- `DocTitle`: Used to transform a lone top level section's title to
  the document title, promote a remaining lone top-level section's
  title to the document subtitle, and determine the document's title
  metadata (document['title']) based on the document title and/or the
  "title" setting.

- `SectionSubTitle`: Used to transform a lone subsection into a
  subtitle.

- `DocInfo`: Used to transform a bibliographic field list into docinfo
  elements.

.. _transforms: https://docutils.sourceforge.io/docs/api/transforms.html
"""

__docformat__ = 'reStructuredText'

import re

from docutils import nodes, parsers, utils
from docutils.transforms import TransformError, Transform


class TitlePromoter(Transform):

    """
    Abstract base class for DocTitle and SectionSubTitle transforms.
    """

    def promote_title(self, node):
        """
        Transform the following tree::

            <node>
                <section>
                    <title>
                    ...

        into ::

            <node>
                <title>
                ...

        `node` is normally a document.
        """
        # Type check
        if not isinstance(node, nodes.Element):
            raise TypeError('node must be of Element-derived type.')

        # `node` must not have a title yet.
        assert not (len(node) and isinstance(node[0], nodes.title))
        section, index = self.candidate_index(node)
        if index is None:
            return False

        # Transfer the section's attributes to the node:
        # NOTE: Change `replace` to False to NOT replace attributes that
        #       already exist in node with those in section.
        # NOTE: Remove `and_source` to NOT copy the 'source'
        #       attribute from section
        node.update_all_atts_concatenating(section, replace=True,
                                           and_source=True)

        # setup_child is called automatically for all nodes.
        node[:] = (section[:1]        # section title
                   + node[:index]     # everything that was in the
                                      # node before the section
                   + section[1:])     # everything that was in the section
        assert isinstance(node[0], nodes.title)
        return True

    def promote_subtitle(self, node):
        """
        Transform the following node tree::

            <node>
                <title>
                <section>
                    <title>
                    ...

        into ::

            <node>
                <title>
                <subtitle>
                ...
        """
        # Type check
        if not isinstance(node, nodes.Element):
            raise TypeError('node must be of Element-derived type.')

        subsection, index = self.candidate_index(node)
        if index is None:
            return False
        subtitle = nodes.subtitle()

        # Transfer the subsection's attributes to the new subtitle
        # NOTE: Change `replace` to False to NOT replace attributes
        #       that already exist in node with those in section.
        # NOTE: Remove `and_source` to NOT copy the 'source'
        #       attribute from section.
        subtitle.update_all_atts_concatenating(subsection, replace=True,
                                               and_source=True)

        # Transfer the contents of the subsection's title to the
        # subtitle:
        subtitle[:] = subsection[0][:]
        node[:] = (node[:1]       # title
                   + [subtitle]
                   # everything that was before the section:
                   + node[1:index]
                   # everything that was in the subsection:
                   + subsection[1:])
        return True

    def candidate_index(self, node):
        """
        Find and return the promotion candidate and its index.

        Return (None, None) if no valid candidate was found.
        """
        index = node.first_child_not_matching_class(
            nodes.PreBibliographic)
        if (index is None or len(node) > (index + 1)
            or not isinstance(node[index], nodes.section)):
            return None, None
        else:
            return node[index], index


class DocTitle(TitlePromoter):

    """
    In reStructuredText_, there is no way to specify a document title
    and subtitle explicitly. Instead, we can supply the document title
    (and possibly the subtitle as well) implicitly, and use this
    two-step transform to "raise" or "promote" the title(s) (and their
    corresponding section contents) to the document level.

    1. If the document contains a single top-level section as its first
       element (instances of `nodes.PreBibliographic` are ignored),
       the top-level section's title becomes the document's title, and
       the top-level section's contents become the document's immediate
       contents. The title is also used for the <document> element's
       "title" attribute default value.

    2. If step 1 successfully determines the document title, we
       continue by checking for a subtitle.

       If the lone top-level section itself contains a single second-level
       section as its first "non-PreBibliographic" element, that section's
       title is promoted to the document's subtitle, and that section's
       contents become the document's immediate contents.

    Example:
       Given this input text::

           =================
            Top-Level Title
           =================

           Second-Level Title
           ~~~~~~~~~~~~~~~~~~

           A paragraph.

       After parsing and running the DocTitle transform, the result is::

           <document names="top-level title">
               <title>
                   Top-Level Title
               <subtitle names="second-level title">
                   Second-Level Title
               <paragraph>
                   A paragraph.

       (Note that the implicit hyperlink target generated by the
       "Second-Level Title" is preserved on the <subtitle> element
       itself.)

    Any `nodes.PreBibliographic` instances occurring before the
    document title or subtitle are accumulated and inserted as
    the first body elements after the title(s).

    .. _reStructuredText: https://docutils.sourceforge.io/rst.html
    """

    default_priority = 320

    def set_metadata(self):
        """
        Set document['title'] metadata title from the following
        sources, listed in order of priority:

        * Existing document['title'] attribute.
        * "title" setting.
        * Document title node (as promoted by promote_title).
        """
        if not self.document.hasattr('title'):
            if self.document.settings.title is not None:
                self.document['title'] = self.document.settings.title
            elif len(self.document) and isinstance(self.document[0],
                                                   nodes.title):
                self.document['title'] = self.document[0].astext()

    def apply(self):
        if self.document.settings.setdefault('doctitle_xform', True):
            # promote_(sub)title defined in TitlePromoter base class.
            if self.promote_title(self.document):
                # If a title has been promoted, also try to promote a
                # subtitle.
                self.promote_subtitle(self.document)
        # Set document['title'].
        self.set_metadata()


class SectionSubTitle(TitlePromoter):

    """
    This works like document subtitles, but for sections.  For example, ::

        <section>
            <title>
                Title
            <section>
                <title>
                    Subtitle
                ...

    is transformed into ::

        <section>
            <title>
                Title
            <subtitle>
                Subtitle
            ...

    For details refer to the docstring of DocTitle.
    """

    default_priority = 350

    def apply(self):
        if not self.document.settings.setdefault('sectsubtitle_xform', True):
            return
        for section in self.document.findall(nodes.section):
            # On our way through the node tree, we are modifying it
            # but only the not-yet-visited part, so that the iterator
            # returned by findall() is not corrupted.
            self.promote_subtitle(section)


class DocInfo(Transform):

    """
    This transform is specific to the reStructuredText_ markup syntax;
    see "Bibliographic Fields" in the `reStructuredText Markup
    Specification`_ for a high-level description. This transform
    should be run *after* the `DocTitle` transform.

    If the document contains a field list as the first element (instances
    of `nodes.PreBibliographic` are ignored), registered bibliographic
    field names are transformed to the corresponding DTD elements,
    becoming child elements of the <docinfo> element (except for a
    dedication and/or an abstract, which become <topic> elements after
    <docinfo>).

    For example, given this document fragment after parsing::

        <document>
            <title>
                Document Title
            <field_list>
                <field>
                    <field_name>
                        Author
                    <field_body>
                        <paragraph>
                            A. Name
                <field>
                    <field_name>
                        Status
                    <field_body>
                        <paragraph>
                            $RCSfile$
            ...

    After running the bibliographic field list transform, the
    resulting document tree would look like this::

        <document>
            <title>
                Document Title
            <docinfo>
                <author>
                    A. Name
                <status>
                    frontmatter.py
            ...

    The "Status" field contained an expanded RCS keyword, which is
    normally (but optionally) cleaned up by the transform. The sole
    contents of the field body must be a paragraph containing an
    expanded RCS keyword of the form "$keyword: expansion text $". Any
    RCS keyword can be processed in any bibliographic field. The
    dollar signs and leading RCS keyword name are removed. Extra
    processing is done for the following RCS keywords:

    - "RCSfile" expands to the name of the file in the RCS or CVS
      repository, which is the name of the source file with a ",v"
      suffix appended. The transform will remove the ",v" suffix.

    - "Date" expands to the format "YYYY/MM/DD hh:mm:ss" (in the UTC
      time zone). The RCS Keywords transform will extract just the
      date itself and transform it to an ISO 8601 format date, as in
      "2000-12-31".

      (Since the source file for this text is itself stored under CVS,
      we can't show an example of the "Date" RCS keyword because we
      can't prevent any RCS keywords used in this explanation from
      being expanded. Only the "RCSfile" keyword is stable; its
      expansion text changes only if the file name changes.)

    .. _reStructuredText: https://docutils.sourceforge.io/rst.html
    .. _reStructuredText Markup Specification:
       https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html
    """

    default_priority = 340

    biblio_nodes = {
          'author': nodes.author,
          'authors': nodes.authors,
          'organization': nodes.organization,
          'address': nodes.address,
          'contact': nodes.contact,
          'version': nodes.version,
          'revision': nodes.revision,
          'status': nodes.status,
          'date': nodes.date,
          'copyright': nodes.copyright,
          'dedication': nodes.topic,
          'abstract': nodes.topic}
    """Canonical field name (lowcased) to node class name mapping for
    bibliographic fields (field_list)."""

    def apply(self):
        if not self.document.settings.setdefault('docinfo_xform', True):
            return
        document = self.document
        index = document.first_child_not_matching_class(
              nodes.PreBibliographic)
        if index is None:
            return
        candidate = document[index]
        if isinstance(candidate, nodes.field_list):
            biblioindex = document.first_child_not_matching_class(
                  (nodes.Titular, nodes.Decorative, nodes.meta))
            nodelist = self.extract_bibliographic(candidate)
            del document[index]         # untransformed field list (candidate)
            document[biblioindex:biblioindex] = nodelist

    def extract_bibliographic(self, field_list):
        docinfo = nodes.docinfo()
        bibliofields = self.language.bibliographic_fields
        labels = self.language.labels
        topics = {'dedication': None, 'abstract': None}
        for field in field_list:
            try:
                name = field[0][0].astext()
                normedname = nodes.fully_normalize_name(name)
                if not (len(field) == 2 and normedname in bibliofields
                        and self.check_empty_biblio_field(field, name)):
                    raise TransformError
                canonical = bibliofields[normedname]
                biblioclass = self.biblio_nodes[canonical]
                if issubclass(biblioclass, nodes.TextElement):
                    if not self.check_compound_biblio_field(field, name):
                        raise TransformError
                    utils.clean_rcs_keywords(
                          field[1][0], self.rcs_keyword_substitutions)
                    docinfo.append(biblioclass('', '', *field[1][0]))
                elif issubclass(biblioclass, nodes.authors):
                    self.extract_authors(field, name, docinfo)
                elif issubclass(biblioclass, nodes.topic):
                    if topics[canonical]:
                        field[-1] += self.document.reporter.warning(
                            'There can only be one "%s" field.' % name,
                            base_node=field)
                        raise TransformError
                    title = nodes.title(name, labels[canonical])
                    title[0].rawsource = labels[canonical]
                    topics[canonical] = biblioclass(
                        '', title, classes=[canonical], *field[1].children)
                else:
                    docinfo.append(biblioclass('', *field[1].children))
            except TransformError:
                if len(field[-1]) == 1 \
                       and isinstance(field[-1][0], nodes.paragraph):
                    utils.clean_rcs_keywords(
                        field[-1][0], self.rcs_keyword_substitutions)
                # if normedname not in bibliofields:
                classvalue = nodes.make_id(normedname)
                if classvalue:
                    field['classes'].append(classvalue)
                docinfo.append(field)
        nodelist = []
        if len(docinfo) != 0:
            nodelist.append(docinfo)
        for name in ('dedication', 'abstract'):
            if topics[name]:
                nodelist.append(topics[name])
        return nodelist

    def check_empty_biblio_field(self, field, name):
        if len(field[-1]) < 1:
            field[-1] += self.document.reporter.warning(
                  f'Cannot extract empty bibliographic field "{name}".',
                  base_node=field)
            return False
        return True

    def check_compound_biblio_field(self, field, name):
        # Check that the `field` body contains a single paragraph
        # (i.e. it must *not* be a compound element).
        f_body = field[-1]
        if len(f_body) == 1 and isinstance(f_body[0], nodes.paragraph):
            return True
        # Restore single author name with initial (E. Xampl) parsed as
        # enumerated list
        # https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#enumerated-lists
        if (isinstance(f_body[0], nodes.enumerated_list)
            and '\n' not in f_body.rawsource.strip()):
            # parse into a dummy document and use created nodes
            _document = utils.new_document('*DocInfo transform*',
                                           field.document.settings)
            parser = parsers.rst.Parser()
            parser.parse('\\'+f_body.rawsource, _document)
            if (len(_document.children) == 1
                and isinstance(_document.children[0], nodes.paragraph)):
                f_body.children = _document.children
                return True
        # Check failed, add a warning
        content = [f'<{e.tagname}>' for e in f_body.children]
        if len(content) > 1:
            content = '[' + ', '.join(content) + ']'
        else:
            content = 'a ' + content[0]
        f_body += self.document.reporter.warning(
                      f'Bibliographic field "{name}"\nmust contain '
                      f'a single <paragraph>, not {content}.',
                      base_node=field)
        return False

    rcs_keyword_substitutions = [
          (re.compile(r'\$' r'Date: (\d\d\d\d)[-/](\d\d)[-/](\d\d)[ T][\d:]+'
                      r'[^$]* \$', re.IGNORECASE), r'\1-\2-\3'),
          (re.compile(r'\$' r'RCSfile: (.+),v \$', re.IGNORECASE), r'\1'),
          (re.compile(r'\$[a-zA-Z]+: (.+) \$'), r'\1')]

    def extract_authors(self, field, name, docinfo):
        try:
            if len(field[1]) == 1:
                if isinstance(field[1][0], nodes.paragraph):
                    authors = self.authors_from_one_paragraph(field)
                elif isinstance(field[1][0], nodes.bullet_list):
                    authors = self.authors_from_bullet_list(field)
                else:
                    raise TransformError
            else:
                authors = self.authors_from_paragraphs(field)
            authornodes = [nodes.author('', '', *author)
                           for author in authors if author]
            if len(authornodes) >= 1:
                docinfo.append(nodes.authors('', *authornodes))
            else:
                raise TransformError
        except TransformError:
            field[-1] += self.document.reporter.warning(
                f'Cannot extract "{name}" from bibliographic field:\n'
                f'Bibliographic field "{name}" must contain either\n'
                ' a single paragraph (with author names separated by one of '
                f'"{"".join(self.language.author_separators)}"),\n'
                ' multiple paragraphs (one per author),\n'
                ' or a bullet list with one author name per item.\n'
                'Note: Leading initials can cause (mis)recognizing names '
                'as enumerated list.',
                base_node=field)
            raise

    def authors_from_one_paragraph(self, field):
        """Return list of Text nodes with author names in `field`.

        Author names must be separated by one of the "autor separators"
        defined for the document language (default: ";" or ",").
        """
        # @@ keep original formatting? (e.g. ``:authors: A. Test, *et-al*``)
        text = ''.join(str(node)
                       for node in field[1].findall(nodes.Text))
        if not text:
            raise TransformError
        for authorsep in self.language.author_separators:
            # don't split at escaped `authorsep`:
            pattern = '(?<!\x00)%s' % authorsep
            authornames = re.split(pattern, text)
            if len(authornames) > 1:
                break
        authornames = (name.strip() for name in authornames)
        return [[nodes.Text(name)] for name in authornames if name]

    def authors_from_bullet_list(self, field):
        authors = []
        for item in field[1][0]:
            if isinstance(item, nodes.comment):
                continue
            if len(item) != 1 or not isinstance(item[0], nodes.paragraph):
                raise TransformError
            authors.append(item[0].children)
        if not authors:
            raise TransformError
        return authors

    def authors_from_paragraphs(self, field):
        for item in field[1]:
            if not isinstance(item, (nodes.paragraph, nodes.comment)):
                raise TransformError
        authors = [item.children for item in field[1]
                   if not isinstance(item, nodes.comment)]
        return authors
