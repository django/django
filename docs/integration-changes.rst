Integration Notes
=================

Django Channels is intended to be merged into Django itself; these are the
planned changes the codebase will need to undertake in that transition.

* The ``channels`` package will become ``django.channels``, and main objects will keep their import path.

* Obviously, the monkeypatches in ``channels.hacks`` will be replaced by
  placing methods onto the objects themselves. The ``request`` and ``response``
  modules will thus no longer exist separately.

Things to ponder
----------------

* The mismatch between signals (broadcast) and channels (single-worker) means
  we should probably leave patching signals into channels for the end developer.
  This would also ensure the speedup improvements for empty signals keep working.
