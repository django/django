Django Channels
===============

Channels is a project to make Django able to handle more than just plain
HTTP requests, including WebSockets and HTTP2, as well as the ability to
run code after a response has been sent for things like thumbnailing or
background calculation.

It's an easy-to-understand extension of the Django view model, and easy
to integrate and deploy.

First, read our :doc:`concepts` documentation to get an idea of the
data model underlying Channels and how they're used inside Django.

Then, read :doc:`getting-started` to see how to get up and running with
WebSockets with only 30 lines of code.

If you want a quick overview, start with :doc:`inshort`.

You can find the Channels repository `on GitHub <http://github.com/andrewgodwin/channels/>`_.

Contents:

.. toctree::
   :maxdepth: 2

   inshort
   concepts
   installation
   getting-started
   deploying
   backends
   testing
   cross-compat
   reference
   faqs
   asgi
