# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.storage
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Storage for the websupport package.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


class StorageBackend(object):
    def pre_build(self):
        """Called immediately before the build process begins. Use this
        to prepare the StorageBackend for the addition of nodes.
        """
        pass

    def has_node(self, id):
        """Check to see if a node exists.

        :param id: the id to check for.
        """
        raise NotImplementedError()

    def add_node(self, id, document, source):
        """Add a node to the StorageBackend.

        :param id: a unique id for the comment.
        :param document: the name of the document the node belongs to.
        :param source: the source files name.
        """
        raise NotImplementedError()

    def post_build(self):
        """Called after a build has completed. Use this to finalize the
        addition of nodes if needed.
        """
        pass

    def add_comment(self, text, displayed, username, time,
                    proposal, node_id, parent_id, moderator):
        """Called when a comment is being added.

        :param text: the text of the comment
        :param displayed: whether the comment should be displayed
        :param username: the name of the user adding the comment
        :param time: a date object with the time the comment was added
        :param proposal: the text of the proposal the user made
        :param node_id: the id of the node that the comment is being added to
        :param parent_id: the id of the comment's parent comment.
        :param moderator: whether the user adding the comment is a moderator
        """
        raise NotImplementedError()

    def delete_comment(self, comment_id, username, moderator):
        """Delete a comment.

        Raises :class:`~sphinxcontrib.websupport.errors.UserNotAuthorizedError`
        if moderator is False and `username` doesn't match the username
        on the comment.

        :param comment_id: The id of the comment being deleted.
        :param username: The username of the user requesting the deletion.
        :param moderator: Whether the user is a moderator.
        """
        raise NotImplementedError()

    def get_metadata(self, docname, moderator):
        """Get metadata for a document. This is currently just a dict
        of node_id's with associated comment counts.

        :param docname: the name of the document to get metadata for.
        :param moderator: whether the requester is a moderator.
        """
        raise NotImplementedError()

    def get_data(self, node_id, username, moderator):
        """Called to retrieve all data for a node. This should return a
        dict with two keys, *source* and *comments* as described by
        :class:`~sphinxcontrib.websupport.WebSupport`'s
        :meth:`~sphinxcontrib.websupport.WebSupport.get_data` method.

        :param node_id: The id of the node to get data for.
        :param username: The name of the user requesting the data.
        :param moderator: Whether the requestor is a moderator.
        """
        raise NotImplementedError()

    def process_vote(self, comment_id, username, value):
        """Process a vote that is being cast. `value` will be either -1, 0,
        or 1.

        :param comment_id: The id of the comment being voted on.
        :param username: The username of the user casting the vote.
        :param value: The value of the vote being cast.
        """
        raise NotImplementedError()

    def update_username(self, old_username, new_username):
        """If a user is allowed to change their username this method should
        be called so that there is not stagnate data in the storage system.

        :param old_username: The username being changed.
        :param new_username: What the username is being changed to.
        """
        raise NotImplementedError()

    def accept_comment(self, comment_id):
        """Called when a moderator accepts a comment. After the method is
        called the comment should be displayed to all users.

        :param comment_id: The id of the comment being accepted.
        """
        raise NotImplementedError()
