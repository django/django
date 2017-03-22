"""
Very partial backport of the `http.HTTPStatus` enum from Python 3.5

This implements just enough of the interface for our purposes, it does not
attempt to be a full implementation.
"""


class HTTPStatus(int):

    phrase = None

    def __new__(cls, code, phrase):
        instance = int.__new__(cls, code)
        instance.phrase = phrase
        return instance


HTTPStatus.OK = HTTPStatus(200, 'OK')
HTTPStatus.NOT_MODIFIED = HTTPStatus(304, 'Not Modified')
HTTPStatus.METHOD_NOT_ALLOWED = HTTPStatus(405, 'Method Not Allowed')
