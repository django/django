from django.db.models import CharField, EmailField, TextField

__all__ = ['CICharField', 'CIEmailField', 'CIText', 'CITextField']


class CIText:
    def db_type(self, connection):
        return 'citext'


class CICharField(CIText, CharField):
    pass


class CIEmailField(CIText, EmailField):
    pass


class CITextField(CIText, TextField):
    pass
