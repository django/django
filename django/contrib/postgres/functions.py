from django.db.models.functions import Func


class Unaccent(Func):
    function = 'UNACCENT'
