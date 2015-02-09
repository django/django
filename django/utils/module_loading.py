# Avoid importing `importlib` from this package.
from __future__ import absolute_import

import copy
import os
import sys
import warnings
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.deprecation import RemovedInDjango19Warning


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError:
        msg = "%s doesn't look like a module path" % dotted_path
        six.reraise(ImportError, ImportError(msg), sys.exc_info()[2])

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError:
        msg = 'Module "%s" does not define a "%s" attribute/class' % (
            dotted_path, class_name)
        six.reraise(ImportError, ImportError(msg), sys.exc_info()[2])


def import_by_path(dotted_path, error_prefix=''):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImproperlyConfigured if something goes wrong.
    """
    warnings.warn(
        'import_by_path() has been deprecated. Use import_string() instead.',
        RemovedInDjango19Warning, stacklevel=2)
    try:
        attr = import_string(dotted_path)
    except ImportError as e:
        msg = '%sError importing module %s: "%s"' % (
            error_prefix, dotted_path, e)
        six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                    sys.exc_info()[2])
    return attr


def autodiscover_modules(*args, **kwargs):
    """
    Auto-discover INSTALLED_APPS modules and fail silently when
    not present. This forces an import on them to register any admin bits they
    may want.

    You may provide a register_to keyword parameter as a way to access a
    registry. This register_to object must have a _registry instance variable
    to access it.
    """
    from django.apps import apps

    register_to = kwargs.get('register_to')
    for app_config in apps.get_app_configs():
        for module_to_search in args:
            # Attempt to import the app's module.
            try:
                if register_to:
                    before_import_registry = copy.copy(register_to._registry)

                import_module('%s.%s' % (app_config.name, module_to_search))
            except:
                # Reset the registry to the state before the last import
                # as this import will have to reoccur on the next request and
                # this could raise NotRegistered and AlreadyRegistered
                # exceptions (see #8245).
                if register_to:
                    register_to._registry = before_import_registry

                # Decide whether to bubble up this error. If the app just
                # doesn't have the module in question, we can ignore the error
                # attempting to import it, otherwise we want it to bubble up.
                if module_has_submodule(app_config.module, module_to_search):
                    raise


if sys.version_info[:2] >= (3, 3):
    if sys.version_info[:2] >= (3, 4):
        from importlib.util import find_spec as importlib_find
    else:
        from importlib import find_loader as importlib_find

    def module_has_submodule(package, module_name):
        """See if 'module' is in 'package'."""
        try:
            package_name = package.__name__
            package_path = package.__path__
        except AttributeError:
            # package isn't a package.
            return False

        full_module_name = package_name + '.' + module_name
        return importlib_find(full_module_name, package_path) is not None

else:
    import imp

    def module_has_submodule(package, module_name):
        """See if 'module' is in 'package'."""
        name = ".".join([package.__name__, module_name])
        try:
            # None indicates a cached miss; see mark_miss() in Python/import.c.
            return sys.modules[name] is not None
        except KeyError:
            pass
        try:
            package_path = package.__path__   # No __path__, then not a package.
        except AttributeError:
            # Since the remainder of this function assumes that we're dealing with
            # a package (module with a __path__), so if it's not, then bail here.
            return False
        for finder in sys.meta_path:
            if finder.find_module(name, package_path):
                return True
        for entry in package_path:
            try:
                # Try the cached finder.
                finder = sys.path_importer_cache[entry]
                if finder is None:
                    # Implicit import machinery should be used.
                    try:
                        file_, _, _ = imp.find_module(module_name, [entry])
                        if file_:
                            file_.close()
                        return True
                    except ImportError:
                        continue
                # Else see if the finder knows of a loader.
                elif finder.find_module(name):
                    return True
                else:
                    continue
            except KeyError:
                # No cached finder, so try and make one.
                for hook in sys.path_hooks:
                    try:
                        finder = hook(entry)
                        # XXX Could cache in sys.path_importer_cache
                        if finder.find_module(name):
                            return True
                        else:
                            # Once a finder is found, stop the search.
                            break
                    except ImportError:
                        # Continue the search for a finder.
                        continue
                else:
                    # No finder found.
                    # Try the implicit import machinery if searching a directory.
                    if os.path.isdir(entry):
                        try:
                            file_, _, _ = imp.find_module(module_name, [entry])
                            if file_:
                                file_.close()
                            return True
                        except ImportError:
                            pass
                    # XXX Could insert None or NullImporter
        else:
            # Exhausted the search, so the module cannot be found.
            return False
