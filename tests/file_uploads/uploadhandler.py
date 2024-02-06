"""
Upload handlers to test the upload API.
"""

import os
from tempfile import NamedTemporaryFile

from django.core.files.uploadhandler import (
    FileUploadHandler,
    StopUpload,
    TemporaryFileUploadHandler,
)


class QuotaUploadHandler(FileUploadHandler):
    """
    This test upload handler terminates the connection if more than a quota
    (5MB) is uploaded.
    """

    QUOTA = 5 * 2**20  # 5 MB

    def __init__(self, request=None):
        super().__init__(request)
        self.total_upload = 0

    def receive_data_chunk(self, raw_data, start):
        self.total_upload += len(raw_data)
        if self.total_upload >= self.QUOTA:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None


class StopUploadTemporaryFileHandler(TemporaryFileUploadHandler):
    """A handler that raises a StopUpload exception."""

    def receive_data_chunk(self, raw_data, start):
        raise StopUpload()


class CustomUploadError(Exception):
    pass


class ErroringUploadHandler(FileUploadHandler):
    """A handler that raises an exception."""

    def receive_data_chunk(self, raw_data, start):
        raise CustomUploadError("Oops!")


class TraversalUploadHandler(FileUploadHandler):
    """A handler with potential directory-traversal vulnerability."""

    def __init__(self, request=None):
        from .tests import UPLOAD_TO

        super().__init__(request)
        self.upload_dir = UPLOAD_TO

    def file_complete(self, file_size):
        self.file.seek(0)
        self.file.size = file_size
        with open(os.path.join(self.upload_dir, self.file_name), "wb") as fp:
            fp.write(self.file.read())
        return self.file

    def new_file(
        self,
        field_name,
        file_name,
        content_type,
        content_length,
        charset=None,
        content_type_extra=None,
    ):
        super().new_file(
            file_name,
            file_name,
            content_length,
            content_length,
            charset,
            content_type_extra,
        )
        self.file = NamedTemporaryFile(suffix=".upload", dir=self.upload_dir)

    def receive_data_chunk(self, raw_data, start):
        self.file.write(raw_data)
