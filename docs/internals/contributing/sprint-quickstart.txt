=======================
Sprint quickstart guide
=======================

This document explains how to prepare to contribute to Django. It is intended
for use during sprints, or by people who are already familiar with contributing
to Python open source projects.

This guide assumes you're familiar with:

* Git (see :doc:`/internals/contributing/writing-code/working-with-git`)
* Managing multiple versions of Python
* Python dependency management, including virtual environments
* The concept of running tests and building documentation

If any of these are unfamiliar, see :doc:`/intro/contributing` for a longer,
step-by-step tutorial.

Set up
======

#. Fork the repository on GitHub, clone your fork to your machine, and
   configure a remote reference to Django's upstream repository:

   .. console::

       $ git clone https://github.com/YourGitHubName/django.git
       $ cd django
       $ git remote add upstream https://github.com/django/django.git

#. Confirm you're using a :ref:`compatible version of Python
   <faq-python-version-support>`, then set up a virtual environment:

   .. code-block:: shell

       $ # This needs to be >= 3.12
       $ python -V
       $ python -m venv ~/.virtualenvs/djangodev
       $ source ~/.virtualenvs/djangodev/bin/activate

   If you are not using a Unix-like system, see the :ref:`platform-specific
   instructions <intro-contributing-install-local-copy>`.

#. Install the dependencies to run the tests and build the documentation:

   .. console::

       $ python -m pip install -U pip
       $ python -m pip install -e . -r tests/requirements/py3.txt -r docs/requirements.txt

#. Install pre-commit hooks so that formatting and linting run automatically
   before each commit:

   .. console::

       $ python -m pip install pre-commit
       $ pre-commit install

   See :ref:`coding-style-pre-commit` for further details.

#. Run the tests:

   .. console::

       $ ./tests/runtests.py

   See :ref:`running-unit-tests` for more information. While tests will all
   pass in CI, they may not on every person's local environment. For example,
   the test suite is only guaranteed to pass on the latest point release of
   each supported Python version. It's possible you may encounter errors using
   an earlier point release.

   If you have a small number of failures, it may be worth investigating
   whether they are known issues, or using the :ref:`django-docker-box
   <running-tests-docker-box>` project to run the tests. Since this is a
   sprint, it may be more valuable for you to work on the issue at hand rather
   than investigating a weird machine configuration problem. Make a note of the
   failing tests before you start, so you can tell whether a later failure was
   caused by your changes.

#. Build the documentation:

   .. console::

       $ cd docs && make html && cd ..

Finding a ticket to work on
===========================

Finding a workable ticket is a challenging task. It's important to read this
section before attempting to do so.

Assessing tickets
-----------------

When looking over tickets, it's a good idea to keep your search to `accepted
tickets created in the last five years`_. Older tickets are old for a reason:
they are usually still open because they are hard, contentious, or both.
You're welcome to try one, but expect it to require a high degree of
perseverance.

Consider using the component filter option in Trac to limit your search to
areas you have used before. If you've used forms in a few Django apps, consider
filtering down to the forms component. Similarly, if you've never worked with
geospatial projects, it's probably wise to avoid ``django.contrib.gis``. For
example, here are the `tickets for the documentation component`_.

.. _accepted tickets created in the last five years: https://code.djangoproject.com/query?stage=Accepted&status=assigned&status=new&time=5+years+ago..today&order=id&desc=1&col=id&col=summary&col=owner&col=type&col=component&col=time&col=changetime
.. _tickets for the documentation component: https://code.djangoproject.com/query?component=Documentation&stage=Accepted&status=assigned&status=new&time=5+years+ago..today&order=id&desc=1&col=id&col=summary&col=owner&col=type&col=component&col=time&col=changetime

Methods to find tickets
-----------------------

There are two recommended ways to find a ticket:

* Look at the `easy pickings`_.
* Use the `vulture method`_.

The vulture method is the process of looking for accepted tickets that haven't
been touched in six months or longer. The ideal ticket has a PR linked to it
that has a code review with explicit requests for changes and the author has
not responded in at least six months on the PR and on the ticket. Before taking
one over, leave a comment on both the ticket and the PR letting the author know
that you are continuing their work.

You can view the list of `possibly vulture-able tickets here`_. The filters
that are applied are:

* Triage stage = Accepted
* Patch needs improvement = Yes
* Created = between ``5 years ago`` and ``today``
* Modified = between ``5 years ago`` and ``6 months ago``

.. _easy pickings: https://code.djangoproject.com/query?easy=1&stage=Accepted&status=assigned&status=new&time=5+years+ago..today&order=id&desc=1&col=id&col=summary&col=owner&col=type&col=component&col=time&col=changetime
.. _vulture method: https://youtube.com/shorts/D6QHet5U82U?si=j5M6sy0ufpeGy_iZ
.. _possibly vulture-able tickets here: https://code.djangoproject.com/query?stage=Accepted&changetime=5+years+ago..6+months+ago&needs_better_patch=1&status=assigned&status=new&time=5+years+ago..today&order=id&desc=1&col=id&col=summary&col=time&col=changetime&col=needs_better_patch&col=owner&col=type&col=component

Claiming a ticket
-----------------

When you find a ticket, make yourself the owner by clicking the "Modify Ticket"
button near the bottom of the page, selecting the "assign to" radio button in
the "Action" section, and clicking "Submit changes". Your username will be
filled in the text box by default. See :ref:`claiming-tickets` for the full
documentation.

Creating a branch for the ticket
================================

How you create your branch depends on whether the ticket already has work
attached to it.

Starting fresh
--------------

With the ticket claimed, create a branch for your work, replacing
``TicketNumber`` with the actual Trac ticket number:

.. console::

    $ git fetch upstream
    $ git checkout -b ticket_TicketNumber upstream/main

When your work is ready, push the branch to your fork and open a pull request.
See :doc:`/internals/contributing/writing-code/submitting-patches` for the full
process.

Continuing someone else's work
------------------------------

If you're continuing the work from someone else's pull request on GitHub,
things can be tricky. You need to pull their branch, but then push it to your
GitHub repository fork.

Run the following, replacing ``PRNumber`` and ``TicketNumber`` with the actual
pull request and Trac ticket numbers:

.. console::

    $ git fetch upstream pull/PRNumber/head:ticket_TicketNumber
    $ git checkout ticket_TicketNumber
    $ git push origin ticket_TicketNumber

For example, to continue PR 8000 for ticket 123, run:

.. console::

    $ git fetch upstream pull/8000/head:ticket_123
    $ git checkout ticket_123
    $ git push origin ticket_123

When preparing your commit, please review our :ref:`committing guidelines
<committing-guidelines>`, specifically how to credit co-authors.
