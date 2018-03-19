class AltersDataBase(type):
    """
    Metaclass to set alters_data attribute to True for methods
    given in data_altering_methods
    """
    data_altering_methods = None

    def __new__(mcs, name, bases, attrs):
        new_cls = super().__new__(mcs, name, bases, attrs)
        update_alters_data(cls=new_cls)
        return new_cls


def update_alters_data(cls):
    """
    Set alters_data attribute to True for methods
    given in cls.data_altering_methods
    """
    data_altering_methods = getattr(cls, 'data_altering_methods', None)
    data_altering_methods = data_altering_methods or ()

    for method in data_altering_methods:
        method_func = getattr(cls, method)
        if not callable(method_func):
            raise ValueError(
                '{} has no method {}'.format(cls, method)
            )

        # Do not override if explicitly set
        if hasattr(method_func, 'alters_data'):
            continue

        setattr(method_func, 'alters_data', True)
