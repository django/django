from io import BytesIO

from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser as _MultiPartParser
from django.utils.datastructures import ImmutableList, MultiValueDict


class BaseParser:
    media_type = None

    def parse(self, request):
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

        request.upload_handlers = ImmutableList(
            request.upload_handlers,
            warning=(
                "You cannot alter upload handlers after the upload has been "
                "processed."
            ),
        )
        parser = _MultiPartParser(
            request.META, data, request.upload_handlers, request.encoding
        )
        _post, _files = parser.parse()
        return _post, _files
