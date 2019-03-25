# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.storage.sqlalchemy_db
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    SQLAlchemy table and mapper definitions used by the
    :class:`sphinxcontrib.websupport.storage.sqlalchemystorage.SQLAlchemyStorage`.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, String, Boolean, \
    ForeignKey, DateTime
from sqlalchemy.orm import relation, sessionmaker, aliased
from sqlalchemy.ext.declarative import declarative_base

if False:
    # For type annotation
    from typing import List  # NOQA

Base = declarative_base()
Session = sessionmaker()

db_prefix = 'sphinx_'


class Node(Base):  # type: ignore
    """Data about a Node in a doctree."""
    __tablename__ = db_prefix + 'nodes'

    id = Column(String(32), primary_key=True)
    document = Column(String(256), nullable=False)
    source = Column(Text, nullable=False)

    def nested_comments(self, username, moderator):
        """Create a tree of comments. First get all comments that are
        descendants of this node, then convert them to a tree form.

        :param username: the name of the user to get comments for.
        :param moderator: whether the user is moderator.
        """
        session = Session()

        if username:
            # If a username is provided, create a subquery to retrieve all
            # votes by this user. We will outerjoin with the comment query
            # with this subquery so we have a user's voting information.
            sq = session.query(CommentVote).\
                filter(CommentVote.username == username).subquery()
            cvalias = aliased(CommentVote, sq)
            q = session.query(Comment, cvalias.value).outerjoin(cvalias)
        else:
            # If a username is not provided, we don't need to join with
            # CommentVote.
            q = session.query(Comment)

        # Filter out all comments not descending from this node.
        q = q.filter(Comment.path.like(str(self.id) + '.%'))

        # Filter out all comments that are not moderated yet.
        if not moderator:
            q = q.filter(Comment.displayed == True)  # noqa

        # Retrieve all results. Results must be ordered by Comment.path
        # so that we can easily transform them from a flat list to a tree.
        results = q.order_by(Comment.path).all()
        session.close()

        return self._nest_comments(results, username)

    def _nest_comments(self, results, username):
        """Given the flat list of results, convert the list into a
        tree.

        :param results: the flat list of comments
        :param username: the name of the user requesting the comments.
        """
        comments = []  # type: List
        list_stack = [comments]
        for r in results:
            if username:
                comment, vote = r
            else:
                comment, vote = (r, 0)

            inheritance_chain = comment.path.split('.')[1:]

            if len(inheritance_chain) == len(list_stack) + 1:
                parent = list_stack[-1][-1]
                list_stack.append(parent['children'])
            elif len(inheritance_chain) < len(list_stack):
                while len(inheritance_chain) < len(list_stack):
                    list_stack.pop()

            list_stack[-1].append(comment.serializable(vote=vote))

        return comments

    def __init__(self, id, document, source):
        self.id = id
        self.document = document
        self.source = source


class CommentVote(Base):  # type: ignore
    """A vote a user has made on a Comment."""
    __tablename__ = db_prefix + 'commentvote'

    username = Column(String(64), primary_key=True)
    comment_id = Column(Integer, ForeignKey(db_prefix + 'comments.id'),
                        primary_key=True)
    # -1 if downvoted, +1 if upvoted, 0 if voted then unvoted.
    value = Column(Integer, nullable=False)

    def __init__(self, comment_id, username, value):
        self.comment_id = comment_id
        self.username = username
        self.value = value


class Comment(Base):  # type: ignore
    """An individual Comment being stored."""
    __tablename__ = db_prefix + 'comments'

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    time = Column(DateTime, nullable=False)
    text = Column(Text, nullable=False)
    displayed = Column(Boolean, index=True, default=False)
    username = Column(String(64))
    proposal = Column(Text)
    proposal_diff = Column(Text)
    path = Column(String(256), index=True)

    node_id = Column(String(32), ForeignKey(db_prefix + 'nodes.id'))
    node = relation(Node, backref="comments")

    votes = relation(CommentVote, backref="comment",
                     cascade="all")

    def __init__(self, text, displayed, username, rating, time,
                 proposal, proposal_diff):
        self.text = text
        self.displayed = displayed
        self.username = username
        self.rating = rating
        self.time = time
        self.proposal = proposal
        self.proposal_diff = proposal_diff

    def set_path(self, node_id, parent_id):
        """Set the materialized path for this comment."""
        # This exists because the path can't be set until the session has
        # been flushed and this Comment has an id.
        if node_id:
            self.node_id = node_id
            self.path = '%s.%s' % (node_id, self.id)
        else:
            session = Session()
            parent_path = session.query(Comment.path).\
                filter(Comment.id == parent_id).one().path
            session.close()
            self.node_id = parent_path.split('.')[0]
            self.path = '%s.%s' % (parent_path, self.id)

    def serializable(self, vote=0):
        """Creates a serializable representation of the comment. This is
        converted to JSON, and used on the client side.
        """
        delta = datetime.now() - self.time

        time = {'year': self.time.year,
                'month': self.time.month,
                'day': self.time.day,
                'hour': self.time.hour,
                'minute': self.time.minute,
                'second': self.time.second,
                'iso': self.time.isoformat(),
                'delta': self.pretty_delta(delta)}

        path = self.path.split('.')
        node = path[0]
        if len(path) > 2:
            parent = path[-2]
        else:
            parent = None

        return {'text': self.text,
                'username': self.username or 'Anonymous',
                'id': self.id,
                'node': node,
                'parent': parent,
                'rating': self.rating,
                'displayed': self.displayed,
                'age': delta.seconds,
                'time': time,
                'vote': vote or 0,
                'proposal_diff': self.proposal_diff,
                'children': []}

    def pretty_delta(self, delta):
        """Create a pretty representation of the Comment's age.
        (e.g. 2 minutes).
        """
        days = delta.days
        seconds = delta.seconds
        hours = seconds / 3600
        minutes = seconds / 60

        if days == 0:
            if hours == 0:
                dt = (minutes, 'minute')
            else:
                dt = (hours, 'hour')
        else:
            dt = (days, 'day')

        if dt[0] == 1:
            ret = '%s %s ago' % dt
        else:
            ret = '%s %ss ago' % dt

        return ret
