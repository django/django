======================================
Reporting bugs and requesting features
======================================

.. Important::

    Please report security issues **only** to
    security@djangoproject.com.  This is a private list only open to
    long-time, highly trusted Django developers, and its archives are
    not public. For further details, please see :doc:`our security
    policies </internals/security>`.


Otherwise, before reporting a bug or requesting a new feature, please consider these
general points:

* Check that someone hasn't already filed the bug or feature request by
  `searching`_ or running `custom queries`_ in the ticket tracker.

* Don't use the ticket system to ask support questions. Use the
  |django-users| list or the `#django`_ IRC channel for that.

* Don't reopen issues that have been marked "wontfix" by a core developer.
  This mark means that the decision has been made that we can't or won't fix
  this particular issue. If you're not sure why, please ask
  on |django-developers|.

* Don't use the ticket tracker for lengthy discussions, because they're
  likely to get lost. If a particular ticket is controversial, please move the
  discussion to |django-developers|.

.. _reporting-bugs:

Reporting bugs
==============

Well-written bug reports are *incredibly* helpful. However, there's a certain
amount of overhead involved in working with any bug tracking system so your
help in keeping our ticket tracker as useful as possible is appreciated. In
particular:

* **Do** read the :doc:`FAQ </faq/index>` to see if your issue might
  be a well-known question.

* **Do** ask on |django-users| or `#django`_ *first* if you're not sure if
  what you're seeing is a bug.

* **Do** write complete, reproducible, specific bug reports. You must
  include a clear, concise description of the problem, and a set of
  instructions for replicating it. Add as much debug information as you can:
  code snippets, test cases, exception backtraces, screenshots, etc. A nice
  small test case is the best way to report a bug, as it gives us an easy
  way to confirm the bug quickly.

* **Don't** post to |django-developers| just to announce that you have
  filed a bug report. All the tickets are mailed to another list,
  |django-updates|, which is tracked by developers and interested
  community members; we see them as they are filed.

To understand the lifecycle of your ticket once you have created it, refer to
:doc:`triaging-tickets`.

Reporting user interface bugs and features
==========================================

If your bug or feature request touches on anything visual in nature, there
are a few additional guidelines to follow:

* Include screenshots in your ticket which are the visual equivalent of a
  minimal testcase. Show off the issue, not the crazy customizations
  you've made to your browser.

* If the issue is difficult to show off using a still image, consider
  capturing a *brief* screencast. If your software permits it, capture only
  the relevant area of the screen.

* If you're offering a patch which changes the look or behavior of Django's
  UI, you **must** attach before *and* after screenshots/screencasts.
  Tickets lacking these are difficult for triagers and core developers to
  assess quickly.

* Screenshots don't absolve you of other good reporting practices. Make sure
  to include URLs, code snippets, and step-by-step instructions on how to
  reproduce the behavior visible in the screenshots.

* Make sure to set the UI/UX flag on the ticket so interested parties can
  find your ticket.

Requesting features
===================

We're always trying to make Django better, and your feature requests are a key
part of that. Here are some tips on how to make a request most effectively:

* Make sure the feature actually requires changes in Django's core. If your
  idea can be developed as an independent application or module — for
  instance, you want to support another database engine — we'll probably
  suggest that you to develop it independently. Then, if your project
  gathers sufficient community support, we may consider it for inclusion in
  Django.

* First request the feature on the |django-developers| list, not in the
  ticket tracker. It'll get read more closely if it's on the mailing list.
  This is even more important for large-scale feature requests. We like to
  discuss any big changes to Django's core on the mailing list before
  actually working on them.

* Describe clearly and concisely what the missing feature is and how you'd
  like to see it implemented. Include example code (non-functional is OK)
  if possible.

* Explain *why* you'd like the feature. In some cases this is obvious, but
  since Django is designed to help real developers get real work done,
  you'll need to explain it, if it isn't obvious why the feature would be
  useful.

If core developers agree on the feature, then it's appropriate to create a
ticket. Include a link the discussion on |django-developers| in the ticket
description.

As with most open-source projects, code talks. If you are willing to write the
code for the feature yourself or, even better, if you've already written it,
it's much more likely to be accepted. Just fork Django on GitHub, create a
feature branch, and show us your work!

See also: :ref:`documenting-new-features`.

.. _how-we-make-decisions:

How we make decisions
=====================

Whenever possible, we strive for a rough consensus. To that end, we'll often
have informal votes on |django-developers| about a feature. In these votes we
follow the voting style invented by Apache and used on Python itself, where
votes are given as +1, +0, -0, or -1. Roughly translated, these votes mean:

* +1: "I love the idea and I'm strongly committed to it."

* +0: "Sounds OK to me."

* -0: "I'm not thrilled, but I won't stand in the way."

* -1: "I strongly disagree and would be very unhappy to see the idea turn
  into reality."

Although these votes on |django-developers| are informal, they'll be taken very
seriously. After a suitable voting period, if an obvious consensus arises we'll
follow the votes.

However, consensus is not always possible. If consensus cannot be reached, or
if the discussion towards a consensus fizzles out without a concrete decision,
any :ref:`core team member <core-team>` may defer the decision to the
:ref:`technical board <technical-board>`.

Internally, the technical board will use the same voting mechanism. A
proposition will be considered carried if:

* There are at least three "+1" votes from members of the technical board.

* There is no "-1" vote from any member of the technical board.

Votes should be submitted within a week.

Since this process allows any technical board member to veto a proposal, a
"-1" vote should be accompanied by an explanation of what it would take to
convert that "-1" into at least a "+0".

Votes on technical matters should be announced and held in public on the
|django-developers| mailing list.

.. _searching: https://code.djangoproject.com/search
.. _custom queries: https://code.djangoproject.com/query
.. _#django: irc://irc.freenode.net/django
