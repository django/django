class NoValidDatabaseException(Exception):
    pass


class UnhealthyDatabaseException(Exception):
    """Exception raised when a database is unhealthy due to an underlying exception."""

    def __init__(self, message, database, original_exception):
        super().__init__(message)
        self.database = database
        self.original_exception = original_exception


class TemporaryUnavailableException(Exception):
    """Exception raised when all databases in setup are temporary unavailable."""

    pass


class InitialHealthCheckFailedError(Exception):
    """Exception raised when initial health check fails."""

    pass
