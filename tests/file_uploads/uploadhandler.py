"""
Upload handlers to test the upload API.
"""

from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class QuotaUploadHandler(FileUploadHandler):
    """
    This test upload handler terminates the connection if more than a quota
    (5MB) is uploaded.
    """

    QUOTA = 5 * 2 ** 20  # 5 MB

    def __init__(self, request=None):
        super(QuotaUploadHandler, self).__init__(request)
        self.total_upload = 0

    def receive_data_chunk(self, raw_data, start):
        self.total_upload += len(raw_data)
        if self.total_upload >= self.QUOTA:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None


class CustomUploadError(Exception):
    pass


class ErroringUploadHandler(FileUploadHandler):
    """A handler that raises an exception."""
    def receive_data_chunk(self, raw_data, start):
        raise CustomUploadError("Oops!")
