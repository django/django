from django.db.models import CharField

__all__ = ['CITextField']


class CITextField(CharField):
    def db_type(self, connection):
        return 'citext'
