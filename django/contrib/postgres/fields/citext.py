from django.db.models import TextField

__all__ = ['CITextField']


class CITextField(TextField):
    def db_type(self, connection):
        return 'citext'
