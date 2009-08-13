import urllib

from django.http import HttpResponseStreaming
from time import sleep

def x():
    for i in range(0, 10):
        yield unicode(i) + u'\n'

def test_streaming(request):
    response = HttpResponseStreaming(content=x(), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=test.csv'
    return response
