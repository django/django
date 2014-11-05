from django.db import models


class NoColumnField(models.AutoField):
    """
    Used when you want to add a column that isn't stricly backed by a db column.
    """

    def __init__(self, *args, **kwargs):
        """
        db_column has to be passed in and point to another column on the model.
        """
        if 'db_column' not in kwargs:
            raise KeyError("You must include a db_column")
        super(NoColumnField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        """
        None indicates do not create an actual field in the database at all.
        """
        return None
