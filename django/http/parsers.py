import json
from io import BytesIO

from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser as _MultiPartParser
from django.utils.datastructures import ImmutableList, MultiValueDict


class BaseParser:
    media_type = None
    parsers = None

    def __init__(self, request):
        self.request = request

    @classmethod
    def can_handle(cls, media_type):
        return media_type == cls.media_type

    def parse(self, data):
        pass


class FormParser(BaseParser):
    media_type = "application/x-www-form-urlencoded"

    def __init__(self, request):
        super().__init__(request)
        # According to RFC 1866, the "application/x-www-form-urlencoded"
        # content type does not have a charset and should be always treated
        # as UTF-8.
        if (
            self.request._encoding is not None
            and self.request._encoding.lower() != "utf-8"
        ):
            raise BadRequest(
                "HTTP requests with the 'application/x-www-form-urlencoded' "
                "content type must be UTF-8 encoded."
            )

    def parse(self, data):
        from django.http import QueryDict

        return QueryDict(data, encoding="utf-8"), MultiValueDict()


class MultiPartParser(BaseParser):
    media_type = "multipart/form-data"

    def parse(self, data):
        request = self.request
        if hasattr(request, "_body"):
            # Use already read data
            request_data = BytesIO(request._body)
        else:
            request_data = request

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
            request.META,
            request_data,
            request.upload_handlers,
            request.encoding,
            self.parsers,
        )
        # TODO _post could also be _data
        _post, _files = parser.parse()
        return _post, _files


class JSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, data):
        def strict_constant(o):
            raise ValueError(
                "Out of range float values are not JSON compliant: " + repr(o)
            )

        return json.loads(data, parse_constant=strict_constant), MultiValueDict()
