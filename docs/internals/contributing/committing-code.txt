===============
Committing code
===============

This section is addressed to the :doc:`/internals/committers` and to anyone
interested in knowing how code gets committed into Django core. If you're a
community member who wants to contribute code to Django, have a look at
:doc:`writing-code/working-with-git` instead.

Commit access
-------------

Django has two types of committers:

Core committers
    These are people who have a long history of contributions to Django's
    codebase, a solid track record of being polite and helpful on the
    mailing lists, and a proven desire to dedicate serious time to Django's
    development. The bar is high for full commit access.

Partial committers
    These are people who are "domain experts." They have direct check-in
    access to the subsystems that fall under their jurisdiction, and they're
    given a formal vote in questions that involve their subsystems. This type
    of access is likely to be given to someone who contributes a large
    sub-framework to Django and wants to continue to maintain it.

    Partial commit access is granted by the same process as full
    committers. However, the bar is set lower; proven expertise in the area
    in question is likely to be sufficient.

Decisions on new committers will follow the process explained in
:ref:`how-we-make-decisions`. To request commit access, please contact an
existing committer privately. Public requests for commit access are potential
flame-war starters, and will simply be ignored.

.. _handling-pull-requests:

Handling pull requests
----------------------

Since Django is now hosted at GitHub, many patches are provided in the form of
pull requests.

When committing a pull request, make sure each individual commit matches the
commit guidelines described below. Contributors are expected to provide the
best pull requests possible. In practice however, committers - who will likely
be more familiar with the commit guidelines - may decide to bring a commit up
to standard themselves.

Here is one way to commit a pull request::

    # Create a new branch tracking upstream/master -- upstream is assumed
    # to be django/django.
    git checkout -b pull_xxxxx upstream/master

    # Download the patches from github and apply them.
    curl https://github.com/django/django/pull/xxxxx.patch | git am

At this point, you can work on the code. Use ``git rebase -i`` and ``git
commit --amend`` to make sure the commits have the expected level of quality.
Once you're ready::

    # Make sure master is ready to receive changes.
    git checkout master
    git pull upstream master
    # Merge the work as "fast-forward" to master, to avoid a merge commit.
    git merge --ff-only pull_xxxxx
    # Check that only the changes you expect will be pushed to upstream.
    git push --dry-run upstream master
    # Push!
    git push upstream master

    # Get rid of the pull_xxxxx branch.
    git branch -d pull_xxxxx

An alternative is to add the contributor's repository as a new remote,
checkout the branch and work from there::

    git remote add <contributor> https://github.com/<contributor>/django.git
    git checkout pull_xxxxx <contributor> <contributor's pull request branch>

Yet another alternative is to fetch the branch without adding the
contributor's repository as a remote::

    git fetch https://github.com/<contributor>/django.git <contributor's pull request branch>
    git checkout -b pull_xxxxx FETCH_HEAD

At this point, you can work on the code and continue as above.

GitHub provides a one-click merge functionality for pull requests. This should
only be used if the pull request is 100% ready, and you have checked it for
errors (or trust the request maker enough to skip checks). Currently, it isn't
possible to check that the tests pass and that the docs build without
downloading the changes to your development environment.

When rewriting the commit history of a pull request, the goal is to make
Django's commit history as usable as possible:

* If a patch contains back-and-forth commits, then rewrite those into one.
  Typically, a commit can add some code, and a second commit can fix
  stylistic issues introduced in the first commit.

* Separate changes to different commits by logical grouping: if you do a
  stylistic cleanup at the same time as you do other changes to a file,
  separating the changes into two different commits will make reviewing
  history easier.

* Beware of merges of upstream branches in the pull requests.

* Tests should pass and docs should build after each commit. Neither the
  tests nor the docs should emit warnings.

* Trivial and small patches usually are best done in one commit. Medium to
  large work should be split into multiple commits if possible.

Practicality beats purity, so it is up to each committer to decide how much
history mangling to do for a pull request. The main points are engaging the
community, getting work done, and having a usable commit history.

.. _committing-guidelines:

Committing guidelines
---------------------

In addition, please follow the following guidelines when committing code to
Django's Git repository:

* Never change the published history of django/django branches! **Never force-
  push your changes to django/django.** If you absolutely must (for security
  reasons for example) first discuss the situation with the core team.

* For any medium-to-big changes, where "medium-to-big" is according to
  your judgment, please bring things up on the |django-developers|
  mailing list before making the change.

  If you bring something up on |django-developers| and nobody responds,
  please don't take that to mean your idea is great and should be
  implemented immediately because nobody contested it. Django's lead
  developers don't have a lot of time to read mailing-list discussions
  immediately, so you may have to wait a couple of days before getting a
  response.

* Write detailed commit messages in the past tense, not present tense.

  * Good: "Fixed Unicode bug in RSS API."
  * Bad: "Fixes Unicode bug in RSS API."
  * Bad: "Fixing Unicode bug in RSS API."

  The commit message should be in lines of 72 chars maximum. There should be
  a subject line, separated by a blank line and then paragraphs of 72 char
  lines. The limits are soft. For the subject line, shorter is better. In the
  body of the commit message more detail is better than less::

      Fixed #18307 -- Added git workflow guidelines

      Refactored the Django's documentation to remove mentions of SVN
      specific tasks. Added guidelines of how to use Git, GitHub, and
      how to use pull request together with Trac instead.

  If the patch wasn't a pull request, you should credit the contributors in
  the commit message: "Thanks A for report, B for the patch and C for the
  review."

* For commits to a branch, prefix the commit message with the branch name.
  For example: "[1.4.x] Fixed #xxxxx -- Added support for mind reading."

* Limit commits to the most granular change that makes sense. This means,
  use frequent small commits rather than infrequent large commits. For
  example, if implementing feature X requires a small change to library Y,
  first commit the change to library Y, then commit feature X in a
  separate commit. This goes a *long way* in helping all core Django
  developers follow your changes.

* Separate bug fixes from feature changes. Bugfixes may need to be backported
  to the stable branch, according to the :ref:`backwards-compatibility policy
  <backwards-compatibility-policy>`.

* If your commit closes a ticket in the Django `ticket tracker`_, begin
  your commit message with the text "Fixed #xxxxx", where "xxxxx" is the
  number of the ticket your commit fixes. Example: "Fixed #123 -- Added
  whizbang feature.". We've rigged Trac so that any commit message in that
  format will automatically close the referenced ticket and post a comment
  to it with the full commit message.

  If your commit closes a ticket and is in a branch, use the branch name
  first, then the "Fixed #xxxxx." For example:
  "[1.4.x] Fixed #123 -- Added whizbang feature."

  For the curious, we're using a `Trac plugin`_ for this.

.. note::

    Note that the Trac integration doesn't know anything about pull requests.
    So if you try to close a pull request with the phrase "closes #400" in your
    commit message, GitHub will close the pull request, but the Trac plugin
    will also close the same numbered ticket in Trac.


.. _Trac plugin: https://github.com/aaugustin/trac-github

* If your commit references a ticket in the Django `ticket tracker`_ but
  does *not* close the ticket, include the phrase "Refs #xxxxx", where "xxxxx"
  is the number of the ticket your commit references. This will automatically
  post a comment to the appropriate ticket.

* Write commit messages for backports using this pattern::

    [<Django version>] Fixed <ticket> -- <description>

    Backport of <revision> from <branch>.

  For example::

    [1.3.x] Fixed #17028 - Changed diveintopython.org -> diveintopython.net.

    Backport of 80c0cbf1c97047daed2c5b41b296bbc56fe1d7e3 from master.

Reverting commits
-----------------

Nobody's perfect; mistakes will be committed.

But try very hard to ensure that mistakes don't happen. Just because we have a
reversion policy doesn't relax your responsibility to aim for the highest
quality possible. Really: double-check your work, or have it checked by
another committer, **before** you commit it in the first place!

When a mistaken commit is discovered, please follow these guidelines:

* If possible, have the original author revert his/her own commit.

* Don't revert another author's changes without permission from the
  original author.

* Use git revert -- this will make a reverse commit, but the original
  commit will still be part of the commit history.

* If the original author can't be reached (within a reasonable amount
  of time -- a day or so) and the problem is severe -- crashing bug,
  major test failures, etc -- then ask for objections on the
  |django-developers| mailing list then revert if there are none.

* If the problem is small (a feature commit after feature freeze,
  say), wait it out.

* If there's a disagreement between the committer and the
  reverter-to-be then try to work it out on the |django-developers|
  mailing list. If an agreement can't be reached then it should
  be put to a vote.

* If the commit introduced a confirmed, disclosed security
  vulnerability then the commit may be reverted immediately without
  permission from anyone.

* The release branch maintainer may back out commits to the release
  branch without permission if the commit breaks the release branch.

* If you mistakenly push a topic branch to django/django, just delete it.
  For instance, if you did: ``git push upstream feature_antigravity``,
  just do a reverse push: ``git push upstream :feature_antigravity``.

.. _ticket tracker: https://code.djangoproject.com/newticket
