from django.db.models.expressions import Func


class JsonEachFunc(Func):
    function = "json_each"
    set_returning = True

    def __init__(self, expression, output_field=None, **extra):
        super().__init__(expression, output_field=output_field, **extra)
