import urllib

from django.http import HttpResponseSendFile

def serve_file(request, filename):
    filename = urllib.unquote(filename)
    return HttpResponseSendFile(filename)