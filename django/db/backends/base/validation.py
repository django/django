class BaseDatabaseValidation:
    """
    This class encapsulates all backend-specific validation.
    """
    def __init__(self, connection):
        self.connection = connection

    def check(self, **kwargs):
        return []

    def check_field(self, field, **kwargs):
        return []
