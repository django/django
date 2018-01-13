from django.db.models import Transform


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'
