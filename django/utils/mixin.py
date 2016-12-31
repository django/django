class AltersDataMixin(type):
    """
    Metaclass mixin to set alters_data attribute to True for methods
    given in data_altering_methods
    """
    data_altering_methods = None

    def __new__(mcs, name, bases, attrs):
        new_cls = super().__new__(mcs, name, bases, attrs)
        data_altering_methods = getattr(new_cls, 'data_altering_methods', None)
        data_altering_methods = data_altering_methods or ()

        for method in data_altering_methods:
            method_func = getattr(new_cls, method, None)
            if not callable(method_func):
                raise ValueError(
                    '{} has no method {}'.format(new_cls, method)
                )

            # Do not override if explicitly set
            if hasattr(method_func, 'alters_data'):
                continue

            setattr(method_func, 'alters_data', True)

        return new_cls
