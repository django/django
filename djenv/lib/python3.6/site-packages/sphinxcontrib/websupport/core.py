# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.core
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Base Module for web support functions.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
import posixpath
from os import path

from six.moves import cPickle as pickle
from jinja2 import Environment, FileSystemLoader
from docutils.core import publish_parts

from sphinx.locale import _
from sphinx.util.osutil import ensuredir
from sphinx.util.jsonimpl import dumps as dump_json
from sphinx.util.pycompat import htmlescape
from sphinxcontrib.websupport import errors
from sphinxcontrib.websupport.search import BaseSearch, SEARCH_ADAPTERS
from sphinxcontrib.websupport.storage import StorageBackend

if False:
    # For type annotation
    from typing import Dict  # NOQA


class WebSupport(object):
    """The main API class for the web support package. All interactions
    with the web support package should occur through this class.
    """
    def __init__(self,
                 srcdir=None,      # only required for building
                 builddir='',      # the dir with data/static/doctrees subdirs
                 datadir=None,     # defaults to builddir/data
                 staticdir=None,   # defaults to builddir/static
                 doctreedir=None,  # defaults to builddir/doctrees
                 search=None,      # defaults to no search
                 storage=None,     # defaults to SQLite in datadir
                 buildername='websupport',
                 confoverrides={},
                 status=sys.stdout,
                 warning=sys.stderr,
                 moderation_callback=None,
                 allow_anonymous_comments=True,
                 docroot='',
                 staticroot='static',
                 ):
        # directories
        self.srcdir = srcdir
        self.builddir = builddir
        self.outdir = path.join(builddir, 'data')
        self.datadir = datadir or self.outdir
        self.staticdir = staticdir or path.join(self.builddir, 'static')
        self.doctreedir = staticdir or path.join(self.builddir, 'doctrees')
        # web server virtual paths
        self.staticroot = staticroot.strip('/')
        self.docroot = docroot.strip('/')

        self.buildername = buildername
        self.confoverrides = confoverrides

        self.status = status
        self.warning = warning
        self.moderation_callback = moderation_callback
        self.allow_anonymous_comments = allow_anonymous_comments

        self._init_templating()
        self._init_search(search)
        self._init_storage(storage)

        self._globalcontext = None  # type: ignore

        self._make_base_comment_options()

    def _init_storage(self, storage):
        if isinstance(storage, StorageBackend):
            self.storage = storage
        else:
            # If a StorageBackend isn't provided, use the default
            # SQLAlchemy backend.
            from sphinxcontrib.websupport.storage.sqlalchemystorage \
                import SQLAlchemyStorage
            if not storage:
                # no explicit DB path given; create default sqlite database
                db_path = path.join(self.datadir, 'db', 'websupport.db')
                ensuredir(path.dirname(db_path))
                storage = 'sqlite:///' + db_path
            self.storage = SQLAlchemyStorage(storage)

    def _init_templating(self):
        import sphinx
        template_path = path.join(sphinx.package_dir,
                                  'themes', 'basic')
        loader = FileSystemLoader(template_path)
        self.template_env = Environment(loader=loader)

    def _init_search(self, search):
        if isinstance(search, BaseSearch):
            self.search = search
        else:
            mod, cls = SEARCH_ADAPTERS[search or 'null']
            mod = 'sphinxcontrib.websupport.search.' + mod
            SearchClass = getattr(__import__(mod, None, None, [cls]), cls)
            search_path = path.join(self.datadir, 'search')
            self.search = SearchClass(search_path)
        self.results_template = \
            self.template_env.get_template('searchresults.html')

    def build(self):
        """Build the documentation. Places the data into the `outdir`
        directory. Use it like this::

            support = WebSupport(srcdir, builddir, search='xapian')
            support.build()

        This will read reStructured text files from `srcdir`. Then it will
        build the pickles and search index, placing them into `builddir`.
        It will also save node data to the database.
        """
        if not self.srcdir:
            raise RuntimeError('No srcdir associated with WebSupport object')

        from sphinx.application import Sphinx
        app = Sphinx(self.srcdir, self.srcdir, self.outdir, self.doctreedir,
                     self.buildername, self.confoverrides, status=self.status,
                     warning=self.warning)
        app.builder.set_webinfo(self.staticdir, self.staticroot,  # type: ignore
                                self.search, self.storage)

        self.storage.pre_build()
        app.build()
        self.storage.post_build()

    def get_globalcontext(self):
        """Load and return the "global context" pickle."""
        if not self._globalcontext:
            infilename = path.join(self.datadir, 'globalcontext.pickle')
            with open(infilename, 'rb') as f:
                self._globalcontext = pickle.load(f)
        return self._globalcontext

    def get_document(self, docname, username='', moderator=False):
        """Load and return a document from a pickle. The document will
        be a dict object which can be used to render a template::

            support = WebSupport(datadir=datadir)
            support.get_document('index', username, moderator)

        In most cases `docname` will be taken from the request path and
        passed directly to this function. In Flask, that would be something
        like this::

            @app.route('/<path:docname>')
            def index(docname):
                username = g.user.name if g.user else ''
                moderator = g.user.moderator if g.user else False
                try:
                    document = support.get_document(docname, username,
                                                    moderator)
                except DocumentNotFoundError:
                    abort(404)
                render_template('doc.html', document=document)

        The document dict that is returned contains the following items
        to be used during template rendering.

        * **body**: The main body of the document as HTML
        * **sidebar**: The sidebar of the document as HTML
        * **relbar**: A div containing links to related documents
        * **title**: The title of the document
        * **css**: Links to css files used by Sphinx
        * **script**: Javascript containing comment options

        This raises :class:`~sphinxcontrib.websupport.errors.DocumentNotFoundError`
        if a document matching `docname` is not found.

        :param docname: the name of the document to load.
        """
        docpath = path.join(self.datadir, 'pickles', docname)
        if path.isdir(docpath):
            infilename = docpath + '/index.fpickle'
            if not docname:
                docname = 'index'
            else:
                docname += '/index'
        else:
            infilename = docpath + '.fpickle'

        try:
            with open(infilename, 'rb') as f:
                document = pickle.load(f)
        except IOError:
            raise errors.DocumentNotFoundError(
                'The document "%s" could not be found' % docname)

        comment_opts = self._make_comment_options(username, moderator)
        comment_meta = self._make_metadata(
            self.storage.get_metadata(docname, moderator))

        document['script'] = comment_opts + comment_meta + document['script']
        return document

    def get_search_results(self, q):
        """Perform a search for the query `q`, and create a set
        of search results. Then render the search results as html and
        return a context dict like the one created by
        :meth:`get_document`::

            document = support.get_search_results(q)

        :param q: the search query
        """
        results = self.search.query(q)
        ctx = {
            'q': q,
            'search_performed': True,
            'search_results': results,
            'docroot': '../',  # XXX
            '_': _,
        }
        document = {
            'body': self.results_template.render(ctx),
            'title': 'Search Results',
            'sidebar': '',
            'relbar': ''
        }
        return document

    def get_data(self, node_id, username=None, moderator=False):
        """Get the comments and source associated with `node_id`. If
        `username` is given vote information will be included with the
        returned comments. The default CommentBackend returns a dict with
        two keys, *source*, and *comments*. *source* is raw source of the
        node and is used as the starting point for proposals a user can
        add. *comments* is a list of dicts that represent a comment, each
        having the following items:

        ============= ======================================================
        Key           Contents
        ============= ======================================================
        text          The comment text.
        username      The username that was stored with the comment.
        id            The comment's unique identifier.
        rating        The comment's current rating.
        age           The time in seconds since the comment was added.
        time          A dict containing time information. It contains the
                      following keys: year, month, day, hour, minute, second,
                      iso, and delta. `iso` is the time formatted in ISO
                      8601 format. `delta` is a printable form of how old
                      the comment is (e.g. "3 hours ago").
        vote          If `user_id` was given, this will be an integer
                      representing the vote. 1 for an upvote, -1 for a
                      downvote, or 0 if unvoted.
        node          The id of the node that the comment is attached to.
                      If the comment's parent is another comment rather than
                      a node, this will be null.
        parent        The id of the comment that this comment is attached
                      to if it is not attached to a node.
        children      A list of all children, in this format.
        proposal_diff An HTML representation of the differences between the
                      the current source and the user's proposed source.
        ============= ======================================================

        :param node_id: the id of the node to get comments for.
        :param username: the username of the user viewing the comments.
        :param moderator: whether the user is a moderator.
        """
        return self.storage.get_data(node_id, username, moderator)

    def delete_comment(self, comment_id, username='', moderator=False):
        """Delete a comment.

        If `moderator` is True, the comment and all descendants will be deleted
        from the database, and the function returns ``True``.

        If `moderator` is False, the comment will be marked as deleted (but not
        removed from the database so as not to leave any comments orphaned), but
        only if the `username` matches the `username` on the comment.  The
        username and text files are replaced with "[deleted]" .  In this case,
        the function returns ``False``.

        This raises :class:`~sphinxcontrib.websupport.errors.UserNotAuthorizedError`
        if moderator is False and `username` doesn't match username on the
        comment.

        :param comment_id: the id of the comment to delete.
        :param username: the username requesting the deletion.
        :param moderator: whether the requestor is a moderator.
        """
        return self.storage.delete_comment(comment_id, username, moderator)

    def add_comment(self, text, node_id='', parent_id='', displayed=True,
                    username=None, time=None, proposal=None,
                    moderator=False):
        """Add a comment to a node or another comment. Returns the comment
        in the same format as :meth:`get_comments`. If the comment is being
        attached to a node, pass in the node's id (as a string) with the
        node keyword argument::

            comment = support.add_comment(text, node_id=node_id)

        If the comment is the child of another comment, provide the parent's
        id (as a string) with the parent keyword argument::

            comment = support.add_comment(text, parent_id=parent_id)

        If you would like to store a username with the comment, pass
        in the optional `username` keyword argument::

            comment = support.add_comment(text, node=node_id,
                                          username=username)

        :param parent_id: the prefixed id of the comment's parent.
        :param text: the text of the comment.
        :param displayed: for moderation purposes
        :param username: the username of the user making the comment.
        :param time: the time the comment was created, defaults to now.
        """
        if username is None:
            if self.allow_anonymous_comments:
                username = 'Anonymous'
            else:
                raise errors.UserNotAuthorizedError()
        parsed = self._parse_comment_text(text)
        comment = self.storage.add_comment(parsed, displayed, username,
                                           time, proposal, node_id,
                                           parent_id, moderator)
        comment['original_text'] = text
        if not displayed and self.moderation_callback:
            self.moderation_callback(comment)
        return comment

    def process_vote(self, comment_id, username, value):
        """Process a user's vote. The web support package relies
        on the API user to perform authentication. The API user will
        typically receive a comment_id and value from a form, and then
        make sure the user is authenticated. A unique username  must be
        passed in, which will also be used to retrieve the user's past
        voting data. An example, once again in Flask::

            @app.route('/docs/process_vote', methods=['POST'])
            def process_vote():
                if g.user is None:
                    abort(401)
                comment_id = request.form.get('comment_id')
                value = request.form.get('value')
                if value is None or comment_id is None:
                    abort(400)
                support.process_vote(comment_id, g.user.name, value)
                return "success"

        :param comment_id: the comment being voted on
        :param username: the unique username of the user voting
        :param value: 1 for an upvote, -1 for a downvote, 0 for an unvote.
        """
        value = int(value)
        if not -1 <= value <= 1:
            raise ValueError('vote value %s out of range (-1, 1)' % value)
        self.storage.process_vote(comment_id, username, value)

    def update_username(self, old_username, new_username):
        """To remain decoupled from a webapp's authentication system, the
        web support package stores a user's username with each of their
        comments and votes. If the authentication system allows a user to
        change their username, this can lead to stagnate data in the web
        support system. To avoid this, each time a username is changed, this
        method should be called.

        :param old_username: The original username.
        :param new_username: The new username.
        """
        self.storage.update_username(old_username, new_username)

    def accept_comment(self, comment_id, moderator=False):
        """Accept a comment that is pending moderation.

        This raises :class:`~sphinxcontrib.websupport.errors.UserNotAuthorizedError`
        if moderator is False.

        :param comment_id: The id of the comment that was accepted.
        :param moderator: Whether the user making the request is a moderator.
        """
        if not moderator:
            raise errors.UserNotAuthorizedError()
        self.storage.accept_comment(comment_id)

    def _make_base_comment_options(self):
        """Helper method to create the part of the COMMENT_OPTIONS javascript
        that remains the same throughout the lifetime of the
        :class:`~sphinxcontrib.websupport.WebSupport` object.
        """
        self.base_comment_opts = {}  # type: Dict[unicode, unicode]

        if self.docroot != '':
            comment_urls = [
                ('addCommentURL', '_add_comment'),
                ('getCommentsURL', '_get_comments'),
                ('processVoteURL', '_process_vote'),
                ('acceptCommentURL', '_accept_comment'),
                ('deleteCommentURL', '_delete_comment')
            ]
            for key, value in comment_urls:
                self.base_comment_opts[key] = \
                    '/' + posixpath.join(self.docroot, value)
        if self.staticroot != 'static':
            static_urls = [
                ('commentImage', 'comment.png'),
                ('closeCommentImage', 'comment-close.png'),
                ('loadingImage', 'ajax-loader.gif'),
                ('commentBrightImage', 'comment-bright.png'),
                ('upArrow', 'up.png'),
                ('upArrowPressed', 'up-pressed.png'),
                ('downArrow', 'down.png'),
                ('downArrowPressed', 'down-pressed.png')
            ]
            for key, value in static_urls:
                self.base_comment_opts[key] = \
                    '/' + posixpath.join(self.staticroot, '_static', value)

    def _make_comment_options(self, username, moderator):
        """Helper method to create the parts of the COMMENT_OPTIONS
        javascript that are unique to each request.

        :param username: The username of the user making the request.
        :param moderator: Whether the user making the request is a moderator.
        """
        rv = self.base_comment_opts.copy()
        if username:
            rv.update({
                'voting': True,
                'username': username,
                'moderator': moderator,
            })
        return '''\
        <script type="text/javascript">
        var COMMENT_OPTIONS = %s;
        </script>
        ''' % dump_json(rv)

    def _make_metadata(self, data):
        return '''\
        <script type="text/javascript">
        var COMMENT_METADATA = %s;
        </script>
        ''' % dump_json(data)

    def _parse_comment_text(self, text):
        settings = {'file_insertion_enabled': False,
                    'raw_enabled': False,
                    'output_encoding': 'unicode'}
        try:
            ret = publish_parts(text, writer_name='html',
                                settings_overrides=settings)['fragment']
        except Exception:
            ret = htmlescape(text)
        return ret
