# -*- coding: utf-8 -*-
"""
To provide a shim layer over Pillow/PIL situation until the PIL support is
removed.


Combinations To Account For
===========================

* Pillow:

    * never has ``_imaging`` under any Python
    * has the ``Image.alpha_composite``, which may aid in detection

* PIL

    * CPython 2.x may have _imaging (& work)
    * CPython 2.x may *NOT* have _imaging (broken & needs a error message)
    * CPython 3.x doesn't work
    * PyPy will *NOT* have _imaging (but works?)

Restated, that looks like:

* If we're on Python 2.x, it could be either Pillow or PIL:

    * If ``import _imaging`` results in ``ImportError``, either they have a
      working Pillow installation or a broken PIL installation, so we need to
      detect further:

        * To detect, we first ``import Image``.
        * If ``Image`` has a ``alpha_composite`` attribute present, only Pillow
          has this, so we assume it's working.
        * If ``Image`` DOES NOT have a ``alpha_composite``attribute, it must be
          PIL & is a broken (likely C compiler-less) install, which we need to
          warn the user about.

    * If ``import _imaging`` works, it must be PIL & is a working install.

* Python 3.x

    * If ``import Image`` works, it must be Pillow, since PIL isn't Python 3.x
      compatible.

* PyPy

    * If ``import _imaging`` results in ``ImportError``, it could be either
      Pillow or PIL, both of which work without it on PyPy, so we're fine.


Approach
========

* Attempt to import ``Image``

    * ``ImportError`` - nothing is installed, toss an exception
    * Either Pillow or the PIL is installed, so continue detecting

* Attempt to ``hasattr(Image, 'alpha_composite')``

    * If it works, it's Pillow & working
    * If it fails, we've got a PIL install, continue detecting

        * The only option here is that we're on Python 2.x or PyPy, of which
          we only care about if we're on CPython.
        * If we're on CPython, attempt to ``import _imaging``

            * ``ImportError`` - Bad install, toss an exception

"""
from __future__ import unicode_literals

import warnings

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _


Image = None
_imaging = None
ImageFile = None


def _detect_image_library():
    global Image
    global _imaging
    global ImageFile

    # Skip re-attempting to import if we've already run detection.
    if Image is not None:
        return Image, _imaging, ImageFile

    # Assume it's not there.
    PIL_imaging = False

    try:
        # Try from the Pillow (or one variant of PIL) install location first.
        from PIL import Image as PILImage
    except ImportError as err:
        try:
            # If that failed, try the alternate import syntax for PIL.
            import Image as PILImage
        except ImportError as err:
            # Neither worked, so it's likely not installed.
            raise ImproperlyConfigured(
                _("Neither Pillow nor PIL could be imported: %s") % err
            )

    # ``Image.alpha_composite`` was added to Pillow in SHA: e414c6 & is not
    # available in any version of the PIL.
    if hasattr(PILImage, 'alpha_composite'):
        PIL_imaging = False
    else:
        # We're dealing with the PIL. Determine if we're on CPython & if
        # ``_imaging`` is available.
        import platform

        # This is the Alex Approved™ way.
        # See http://mail.python.org/pipermail//pypy-dev/2011-November/008739.html
        if platform.python_implementation().lower() == 'cpython':
            # We're on CPython (likely 2.x). Since a C compiler is needed to
            # produce a fully-working PIL & will create a ``_imaging`` module,
            # we'll attempt to import it to verify their kit works.
            try:
                import _imaging as PIL_imaging
            except ImportError as err:
                raise ImproperlyConfigured(
                    _("The '_imaging' module for the PIL could not be "
                      "imported: %s") % err
                )

    # Try to import ImageFile as well.
    try:
        from PIL import ImageFile as PILImageFile
    except ImportError:
        import ImageFile as PILImageFile

    # Finally, warn about deprecation...
    if PIL_imaging is not False:
        warnings.warn(
            "Support for the PIL will be removed in Django 1.8. Please " +
            "uninstall it & install Pillow instead.",
            PendingDeprecationWarning
        )

    return PILImage, PIL_imaging, PILImageFile


Image, _imaging, ImageFile = _detect_image_library()
