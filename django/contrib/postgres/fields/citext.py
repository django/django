from django.db.models import CharField, EmailField, TextField

__all__ = ['CICharField', 'CIEmailField', 'CIText', 'CITextField']


class cistr(str):

    """
    a string type that allows case insensitive comparisons
    """

    def __eq__(self, other):
        if isinstance(other, str):
            return self.casefold() == other.casefold()

        return super().__eq__(other)


class CIText:

    def get_internal_type(self):
        return 'CI' + super().get_internal_type()

    def db_type(self, connection):
        return 'citext'

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if add and value:
            value = cistr(value)
            setattr(model_instance, self.attname, value)

        return value

    def value_to_cistr(self, value):
        if isinstance(value, cistr) or value is None:
            return value
        return cistr(value)

    def from_db_value(self, value, expression, connection):
        return self.value_to_cistr(value)

    def to_python(self, value):
        return self.value_to_cistr(value)


class CICharField(CIText, CharField):
    pass


class CIEmailField(CIText, EmailField):
    pass


class CITextField(CIText, TextField):
    pass
