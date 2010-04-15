import os
import imp

def module_has_submodule(mod, submod_name):
    # If the module was loaded from an egg, __loader__ will be set and 
    # its find_module must be used to search for submodules.
    loader = getattr(mod, '__loader__', None)
    if loader:
        mod_path = "%s.%s" % (mod.__name__, submod_name)
        mod_path = mod_path[len(loader.prefix):]
        x = loader.find_module(mod_path)
        if x is None:
            # zipimport.zipimporter.find_module is documented to take
            # dotted paths but in fact through Pyton 2.7 is observed 
            # to require os.sep in place of dots...so try using os.sep
            # if the dotted path version failed to find the requested 
            # submodule.
            x = loader.find_module(mod_path.replace('.', os.sep))
        return x is not None

    try:
        imp.find_module(submod_name, mod.__path__)
        return True
    except ImportError:
        return False


