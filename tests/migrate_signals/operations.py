from django.db import migrations


class Operation0(migrations.RunPython):
    def __eq__(self, operation):
        return self.__class__ == operation.__class__

    def __init__(self):
        super().__init__(self.dummy, self.dummy)

    def dummy(self, apps, schema_editor):
        pass


class Operation1(Operation0):
    pass


class Operation2(Operation0):
    pass


class Operation3(Operation0):
    pass
