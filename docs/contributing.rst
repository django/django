Contributing
============

If you're looking to contribute to Channels, then please read on - we encourage
contributions both large and small, from both novice and seasoned developers.


What can I work on?
-------------------

We're looking for help with the following areas:

 * Documentation and tutorial writing
 * Bugfixing and testing
 * Feature polish and occasional new feature design
 * Case studies and writeups

You can find what we're looking to work on in the GitHub issues list for each
of the Channels sub-projects:

 * `Channels issues <https://github.com/django/channels/issues/>`_, for the Django integration and overall project efforts
 * `Daphne issues <https://github.com/django/daphne/issues/>`_, for the HTTP and Websocket termination
 * `asgiref issues <https://github.com/django/asgiref/issues/>`_, for the base ASGI library/memory backend
 * `channels_redis issues <https://github.com/django/channels_redis/issues/>`_, for the Redis channel backend

Issues are categorized by difficulty level:

 * ``exp/beginner``: Easy issues suitable for a first-time contributor.
 * ``exp/intermediate``: Moderate issues that need skill and a day or two to solve.
 * ``exp/advanced``: Difficult issues that require expertise and potentially weeks of work.

They are also classified by type:

 * ``documentation``: Documentation issues. Pick these if you want to help us by writing docs.
 * ``bug``: A bug in existing code. Usually easier for beginners as there's a defined thing to fix.
 * ``enhancement``: A new feature for the code; may be a bit more open-ended.

You should filter the issues list by the experience level and type of work
you'd like to do, and then if you want to take something on leave a comment
and assign yourself to it. If you want advice about how to take on a bug,
leave a comment asking about it, or pop into the IRC channel at
``#django-channels`` on Freenode and we'll be happy to help.

The issues are also just a suggested list - any offer to help is welcome as long
as it fits the project goals, but you should make an issue for the thing you
wish to do and discuss it first if it's relatively large (but if you just found
a small bug and want to fix it, sending us a pull request straight away is fine).


I'm a novice contributor/developer - can I help?
------------------------------------------------

Of course! The issues labelled with ``exp/beginner`` are a perfect place to
get started, as they're usually small and well defined. If you want help with
one of them, pop into the IRC channel at ``#django-channels`` on Freenode or
get in touch with Andrew directly at andrew@aeracode.org.


How do I get started and run the tests?
---------------------------------------

First, you should first clone the git repository to a local directory::

    git clone https://github.com/django/channels.git channels

Next, you may want to make a virtual environment to run the tests and develop
in; you can use either ``virtualenvwrapper``, ``pipenv`` or just plain
``virtualenv`` for this.

Then, ``cd`` into the ``channels`` directory and install it editable into
your environment::

    cd channels/
    pip install -e .[tests]

Note the ``[tests]`` section there; that tells ``pip`` that you want to install
the ``tests`` extra, which will bring in testing depedencies like
``pytest-django``.

Then, you can run the tests::

    pytest


Can you pay me for my time?
---------------------------

Thanks to Mozilla, we have a reasonable budget to pay people for their time
working on all of the above sorts of tasks and more. Generally, we'd prefer
to fund larger projects (you can find these labelled as ``epic-project`` in the
issues lists) to reduce the administrative overhead, but we're open to any
proposal.

If you're interested in working on something and being paid, you'll need to
draw up a short proposal and get in touch with the committee, discuss the work
and your history with open-source contribution (we strongly prefer that you have
a proven track record on at least a few things) and the amount you'd like to be paid.

If you're interested in working on one of these tasks, get in touch with
Andrew Godwin (andrew@aeracode.org) as a first point of contact; he can help
talk you through what's involved, and help judge/refine your proposal before
it goes to the committee.

Tasks not on any issues list can also be proposed; Andrew can help talk about them
and if they would be sensible to do.
