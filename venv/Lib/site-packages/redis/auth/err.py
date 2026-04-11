from typing import Iterable


class RequestTokenErr(Exception):
    """
    Represents an exception during token request.
    """

    def __init__(self, *args):
        super().__init__(*args)


class InvalidTokenSchemaErr(Exception):
    """
    Represents an exception related to invalid token schema.
    """

    def __init__(self, missing_fields: Iterable[str] = []):
        super().__init__(
            "Unexpected token schema. Following fields are missing: "
            + ", ".join(missing_fields)
        )


class TokenRenewalErr(Exception):
    """
    Represents an exception during token renewal process.
    """

    def __init__(self, *args):
        super().__init__(*args)
