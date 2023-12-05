import json
from io import BytesIO

from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser as _MultiPartParser
from django.utils.datastructures import ImmutableList, MultiValueDict


class BaseParser:
    media_type = None
    parsers = None

    def can_handle(self, media_type):
        return media_type == self.media_type

    def parse(self, data, request=None):
        pass


class FormParser(BaseParser):
    media_type = "application/x-www-form-urlencoded"

    def parse(self, request):
        from django.http import QueryDict

        # According to RFC 1866, the "application/x-www-form-urlencoded"
        # content type does not have a charset and should be always treated
        # as UTF-8.
        if request._encoding is not None and request._encoding.lower() != "utf-8":
            raise BadRequest(
                "HTTP requests with the 'application/x-www-form-urlencoded' "
                "content type must be UTF-8 encoded."
            )
        return QueryDict(request.body, encoding="utf-8"), MultiValueDict()


class MultiPartParser(BaseParser):
    media_type = "multipart/form-data"

    def parse(self, request):
        if hasattr(request, "_body"):
            # Use already read data
            data = BytesIO(request._body)
        else:
            data = request

        # TODO - POST and data can be called on the same request. This parser can be
        # called multiple times on the same request. While `_post` `_data` are different
        # _files is the same. Allow parsing them twice, but don't change the handlers?
        if not hasattr(request, "_files"):
            request.upload_handlers = ImmutableList(
                request.upload_handlers,
                warning=(
                    "You cannot alter upload handlers after the upload has been "
                    "processed."
                ),
            )
        parser = _MultiPartParser(
            request.META, data, request.upload_handlers, request.encoding, self.parsers
        )
        # TODO _post could also be _data
        _post, _files = parser.parse()
        return _post, _files


class JSONParser(BaseParser):
    media_type = "application/json"

    # TODO rename request -- it's not always one.
    def parse(self, request):
        from django.http import HttpRequest

        def strict_constant(o):
            raise ValueError(
                "Out of range float values are not JSON compliant: " + repr(o)
            )

        if isinstance(request, HttpRequest):
            request = request.body
        return json.loads(request, parse_constant=strict_constant), MultiValueDict()
