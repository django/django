"""
This module contains generic exceptions used by template backends. Although,
due to historical reasons, the Django template language also internally uses
these exceptions, other exceptions specific to the DTL should not be added
here.
"""


class TemplateDoesNotExist(Exception):
    """
    The exception used when a template does not exist. Optional arguments:

    backend
        The template backend class used when raising this exception.

    tried
        A list of sources that were tried when finding the template. This
        is formatted as a list of tuples containing (origin, status), where
        origin is an Origin object or duck type and status is a string with the
        reason the template wasn't found.

    chain
        A list of intermediate TemplateDoesNotExist exceptions. This is used to
        encapsulate multiple exceptions when loading templates from multiple
        engines.
    """

    def __init__(self, msg, tried=None, backend=None, chain=None):
        self.backend = backend
        self.tried = tried or []
        self.chain = chain or []
        super().__init__(msg)

    def __str__(self):
        base_msg = super().__str__()
        if self.tried:
            tried_sources = ", ".join(
                f"{origin} ({status})" for origin, status in self.tried
            )
            return f"{base_msg} | Tried: {tried_sources}"
        return base_msg


class TemplateSyntaxError(Exception):
    """
    The exception used for syntax errors during parsing or rendering.
    """

    def __init__(self, msg, line_number=None):
        self.line_number = line_number
        super().__init__(msg)

    def __str__(self):
        base_msg = super().__str__()
        if self.line_number is not None:
            return f"Syntax error at line {self.line_number}: {base_msg}"
        return base_msg
