Support
=======

If you have questions about Channels, need debugging help or technical support, you can turn to community resources like:

- `Stack Overflow <https://www.stackoverflow.com>`_
- The `Django Users mailing list <https://groups.google.com/forum/#!forum/django-users>`_ (django-users@googlegroups.com)
- The Channels support channel on the `PySlackers Slack group <https://pyslackers.com/>`_

If you have a concrete bug or feature request (one that is clear and actionable), please file an issue against the
appropriate GitHub project.

Unfortunately, if you open a GitHub issue with a vague problem (like "it's slow!" or "connections randomly drop!")
we'll have to close it as we don't have the volunteers to answer the number of questions we'd get - please go to
one of the other places above for support from the community at large.

As a guideline, your issue is concrete enough to open an issue if you can provide **exact steps to reproduce** in a fresh,
example project. We need to be able to reproduce it on a *normal, local developer machine* - so saying something doesn't
work in a hosted environment is unfortunately not very useful to us, and we'll close the issue and point you here.

Apologies if this comes off as harsh, but please understand that open source maintenance and support takes up a lot
of time, and if we answered all the issues and support requests there would be no time left to actually work on the code
itself!

Making bugs reproducible
------------------------

If you're struggling with an issue that only happens in a production environment and can't get it to reproduce locally
so either you can fix it or someone can help you, take a step-by-step approach to eliminating the differences between the
environments.

First off, try changing your production environment to see if that helps - for example, if you have Nginx/Apache/etc.
between browsers and Channels, try going direct to the Python server and see if that fixes things. Turn SSL off if you
have it on. Try from different browsers and internet connections. WebSockets are notoriously hard to debug already,
and so you should expect some level of akwardness from any project involving them.

Next, check package versions between your local and remote environments. You'd be surprised how easy it is to forget
to upgrade something!

Once you've made sure it's none of that, try changing your project. Make a fresh Django project (or use one of the
Channels example projects) and make sure it doesn't have the bug, then work on adding code to it from your project
until the bug appears. Alternately, take your project and remove pieces back down to the basic Django level until
it works.

Network programming is also just difficult in general; you should expect some level of reconnects and dropped connections
as a matter of course. Make sure that what you're seeing isn't just normal for a production application.

How to help the Channels project
--------------------------------

If you'd like to help us with support, the first thing to do is to provide support in the communities mentioned at the
top (Stack Overflow and the mailing list).

If you'd also like to help triage issues, please get in touch and mention you'd like to help out and we can make sure you're
set up and have a good idea of what to do. Most of the work is making sure incoming issues are actually valid and actionable,
and closing those that aren't and redirecting them to this page politely and explaining why.

Some sample response templates are below.

General support request
~~~~~~~~~~~~~~~~~~~~~~~

::

    Sorry, but we can't help out with general support requests here - the issue tracker is for reproduceable bugs and
    concrete feature requests only! Please see our support documentation (http://channels.readthedocs.io/en/latest/support.html)
    for more information about where you can get general help.

Non-specific bug/"It doesn't work!"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    I'm afraid we can't address issues without either direct steps to reproduce, or that only happen in a production
    environment, as they may not be problems in the project itself. Our support documentation
    (http://channels.readthedocs.io/en/latest/support.html) has details about how to take this sort of problem, diagnose it,
    and either fix it yourself, get help from the community, or make it into an actionable issue that we can handle.

    Sorry we have to direct you away like this, but we get a lot of support requests every week. If you can reduce the problem
    to a clear set of steps to reproduce or an example project that fails in a fresh environment, please re-open the ticket
    with that information.

Problem in application code
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    It looks like a problem in your application code rather than in Channels itself, so I'm going to close the ticket.
    If you can trace it down to a problem in Channels itself (with exact steps to reproduce on a fresh or small example
    project - see http://channels.readthedocs.io/en/latest/support.html) please re-open the ticket! Thanks.
