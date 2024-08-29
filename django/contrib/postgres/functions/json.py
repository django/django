from django.db.models import CharField, Func, IntegerField, JSONField


class JSONArrayLength(Func):
    function = "jsonb_array_length"
    output_field = IntegerField()


class JSONConcat(Func):
    template = "%(expressions)s"
    output_field = JSONField()
    arg_joiner = " || "


class JSONDeleteKey(Func):
    template = "%(expressions)s"
    output_field = JSONField()
    arg_joiner = " - "

class JSONBuildArray(Func):
    function = "jsonb_build_array"
    output_field = JSONField()


class JSONArrayElements(Func):
    function = "jsonb_array_elements"
    arity = 1
    output_field = JSONField()


class JSONExtractPath(Func):
    function = "jsonb_extract_path"
    arity = 2
    output_field = JSONField()


class JSONExtractPathText(Func):
    function = "jsonb_extract_path_text"
    arity = 2
    output_field = CharField()
