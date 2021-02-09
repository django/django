from io import BytesIO

from django.http import FileResponse

FILE_RESPONSE_HOLDER = {}


def file_response(request):
    f1 = BytesIO(b"test1")
    f2 = BytesIO(b"test2")
    response = FileResponse(f1)
    response._resource_closers.append(f2.close)
    FILE_RESPONSE_HOLDER['response'] = response
    FILE_RESPONSE_HOLDER['buffers'] = (f1, f2)
    return response
