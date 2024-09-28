from django.db.migrations.operations.base import Operation


class TestOperation(Operation):
    def __init__(self):
        pass

    def deconstruct(self):
        return (self.__class__.__name__, [], {})

    @property
    def reversible(self):
        return True

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def state_backwards(self, app_label, state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass


class CreateModel(TestOperation):
    pass


class ArgsOperation(TestOperation):
    def __init__(self, arg1, arg2):
        self.arg1, self.arg2 = arg1, arg2

    def deconstruct(self):
        return (self.__class__.__name__, [self.arg1, self.arg2], {})


class KwargsOperation(TestOperation):
    def __init__(self, kwarg1=None, kwarg2=None):
        self.kwarg1, self.kwarg2 = kwarg1, kwarg2

    def deconstruct(self):
        kwargs = {}
        if self.kwarg1 is not None:
            kwargs["kwarg1"] = self.kwarg1
        if self.kwarg2 is not None:
            kwargs["kwarg2"] = self.kwarg2
        return (self.__class__.__name__, [], kwargs)


class ArgsKwargsOperation(TestOperation):
    def __init__(self, arg1, arg2, kwarg1=None, kwarg2=None):
        self.arg1, self.arg2 = arg1, arg2
        self.kwarg1, self.kwarg2 = kwarg1, kwarg2

    def deconstruct(self):
        kwargs = {}
        if self.kwarg1 is not None:
            kwargs["kwarg1"] = self.kwarg1
        if self.kwarg2 is not None:
            kwargs["kwarg2"] = self.kwarg2
        return (
            self.__class__.__name__,
            [self.arg1, self.arg2],
            kwargs,
        )


class ArgsAndKeywordOnlyArgsOperation(ArgsKwargsOperation):
    def __init__(self, arg1, arg2, *, kwarg1, kwarg2):
        super().__init__(arg1, arg2, kwarg1=kwarg1, kwarg2=kwarg2)


class ExpandArgsOperation(TestOperation):
    serialization_expand_args = ["arg"]

    def __init__(self, arg):
        self.arg = arg

    def deconstruct(self):
        return (self.__class__.__name__, [self.arg], {})
