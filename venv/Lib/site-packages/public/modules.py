def populate_all() -> None:
    """Populate the calling module's __all__ with all of its public names.

    The criteria for what is a public name is derived from various common linter rules, although
    it's not an exact science.

    * The name does not start with an underscore.
    * The name is not bound to a module object.  This prevents imported modules from being added.
    * The object the name is bound to does not appear to be defined in some other module.  This
      prevents most from-imports from being added, but note that this can be fooled if you import
      simple types (such as an ``int`` or a ``str``) from another module (e.g. ``from sys import
      abiflags``), because simple types don't have a ``__module__`` attribute.

    If you find that some names are missing from the list, you can add them to __all__ explicitly by
    using the @public decorator.  If you find some names in __all__ that should not be present,
    decorate them with the @private decorator.

    This function respects any existing __all__ in your module.

    Typical usage is to call this function at the bottom of your module.
    """
    # Import this here rather than at module scope so we don't pay the import cost just to export
    # this function in the `public` package namespace.
    import inspect

    frameinfo_called_in = inspect.stack()[1]

    if (module := inspect.getmodule(frameinfo_called_in.frame)) is None:
        return

    mdict = frameinfo_called_in.frame.f_globals
    dunder_all = mdict.setdefault('__all__', [])
    seen = set(dunder_all)

    for name, binding in mdict.items():
        if name.startswith('_'):
            continue

        if inspect.ismodule(binding):
            continue

        # Don't export objects imported from other modules.  Simple types won't have a module.  Note
        # that simple types imported with `from import module *` will show up in __all__.
        if inspect.getmodule(binding) not in (module, None):
            continue

        # We don't want to add names to the list twice, but we do want to preserve the order of any
        # existing __all__ strings.
        if name not in seen:
            dunder_all.append(name)
            seen.add(name)
