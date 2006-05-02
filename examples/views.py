from django import http

def index(request):
    r = http.HttpResponse('<h1>Django examples</h1><ul>')
    r.write('<li><a href="hello/html/">Hello world (HTML)</a></li>')
    r.write('<li><a href="hello/text/">Hello world (text)</a></li>')
    r.write('<li><a href="hello/write/">HttpResponse objects are file-like objects</a></li>')
    r.write('<li><a href="hello/metadata/">Displaying request metadata</a></li>')
    r.write('<li><a href="hello/getdata/">Displaying GET data</a></li>')
    r.write('<li><a href="hello/postdata/">Displaying POST data</a></li>')
    r.write('</ul>')
    return r
