from django.db.models import Transform


class Unaccent(Transform):
    bilateral = True
    lookup_name = 'unaccent'

    def as_postgresql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "UNACCENT(%s)" % lhs, params
