import datetime
import types
from django.db import models


class MigrationWriter(object):
    """
    Takes a Migration instance and is able to produce the contents
    of the migration file from it.
    """

    def __init__(self, migration):
        self.migration = migration

    def as_string(self):
        """
        Returns a string of the file contents.
        """
        items = {
            "dependencies": repr(self.migration.dependencies),
        }
        imports = set()
        # Deconstruct operations
        operation_strings = []
        for operation in self.migration.operations:
            name, args, kwargs = operation.deconstruct()
            arg_strings = []
            for arg in args:
                arg_string, arg_imports = self.serialize(arg)
                arg_strings.append(arg_string)
                imports.update(arg_imports)
            for kw, arg in kwargs.items():
                arg_string, arg_imports = self.serialize(arg)
                imports.update(arg_imports)
                arg_strings.append("%s = %s" % (kw, arg_string))
            operation_strings.append("migrations.%s(%s\n        )" % (name, "".join("\n            %s," % arg for arg in arg_strings)))
        items["operations"] = "[%s\n    ]" % "".join("\n        %s," % s for s in operation_strings)
        # Format imports nicely
        if not imports:
            items["imports"] = ""
        else:
            items["imports"] = "\n".join(imports) + "\n"
        return MIGRATION_TEMPLATE % items

    @property
    def filename(self):
        return "%s.py" % self.migration.name

    @classmethod
    def serialize(cls, value):
        """
        Serializes the value to a string that's parsable by Python, along
        with any needed imports to make that string work.
        More advanced than repr() as it can encode things
        like datetime.datetime.now.
        """
        # Sequences
        if isinstance(value, (list, set, tuple)):
            imports = set()
            strings = []
            for item in value:
                item_string, item_imports = cls.serialize(item)
                imports.update(item_imports)
                strings.append(item_string)
            if isinstance(value, set):
                format = "set([%s])"
            elif isinstance(value, tuple):
                format = "(%s,)"
            else:
                format = "[%s]"
            return format % (", ".join(strings)), imports
        # Dictionaries
        elif isinstance(value, dict):
            imports = set()
            strings = []
            for k, v in value.items():
                k_string, k_imports = cls.serialize(k)
                v_string, v_imports = cls.serialize(v)
                imports.update(k_imports)
                imports.update(v_imports)
                strings.append((k_string, v_string))
            return "{%s}" % (", ".join(["%s: %s" % (k, v) for k, v in strings])), imports
        # Datetimes
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return repr(value), set(["import datetime"])
        # Simple types
        elif isinstance(value, (int, long, float, str, unicode, bool, types.NoneType)):
            return repr(value), set()
        # Django fields
        elif isinstance(value, models.Field):
            attr_name, path, args, kwargs = value.deconstruct()
            module, name = path.rsplit(".", 1)
            if module == "django.db.models":
                imports = set()
            else:
                imports = set("import %s" % module)
                name = path
            arg_strings = []
            for arg in args:
                arg_string, arg_imports = cls.serialize(arg)
                arg_strings.append(arg_string)
                imports.update(arg_imports)
            for kw, arg in kwargs.items():
                arg_string, arg_imports = cls.serialize(arg)
                imports.update(arg_imports)
                arg_strings.append("%s=%s" % (kw, arg_string))
            return "%s(%s)" % (name, ", ".join(arg_strings)), imports
        # Functions
        elif isinstance(value, (types.FunctionType, types.BuiltinFunctionType)):
            # Special-cases, as these don't have im_class
            special_cases = [
                (datetime.datetime.now, "datetime.datetime.now", ["import datetime"]),
                (datetime.datetime.utcnow, "datetime.datetime.utcnow", ["import datetime"]),
                (datetime.date.today, "datetime.date.today", ["import datetime"]),
            ]
            for func, string, imports in special_cases:
                if func == value:  # For some reason "utcnow is not utcnow"
                    return string, set(imports)
            # Method?
            if hasattr(value, "im_class"):
                klass = value.im_class
                module = klass.__module__
                return "%s.%s.%s" % (module, klass.__name__, value.__name__), set(["import %s" % module])
            else:
                module = value.__module__
                if module is None:
                    raise ValueError("Cannot serialize function %r: No module" % value)
                return "%s.%s" % (module, value.__name__), set(["import %s" % module])
        # Uh oh.
        else:
            raise ValueError("Cannot serialize: %r" % value)


MIGRATION_TEMPLATE = """# encoding: utf8
from django.db import models, migrations
%(imports)s

class Migration(migrations.Migration):

    dependencies = %(dependencies)s

    operations = %(operations)s
"""
