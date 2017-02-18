class BaseDatabaseValidation(object):
    """
    This class encapsulates all backend-specific model validation.
    """
    def __init__(self, connection):
        self.connection = connection

    def check_field(self, field, **kwargs):
        return []
