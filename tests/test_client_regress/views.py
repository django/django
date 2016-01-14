import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.test import Client
from django.test.client import CONTENT_TYPE_RE
from django.test.utils import setup_test_environment
from django.utils.six.moves.urllib.parse import urlencode


class CustomTestException(Exception):
    pass


def no_template_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    return HttpResponse("No template used. Sample content: twice once twice. Content ends.")


def staff_only_view(request):
    "A view that can only be visited by staff. Non staff members get an exception"
    if request.user.is_staff:
        return HttpResponse('')
    else:
        raise CustomTestException()


def get_view(request):
    "A simple login protected view"
    return HttpResponse("Hello world")
get_view = login_required(get_view)


def request_data(request, template='base.html', data='sausage'):
    "A simple view that returns the request data in the context"
    return render(request, template, {
        'get-foo': request.GET.get('foo'),
        'get-bar': request.GET.get('bar'),
        'post-foo': request.POST.get('foo'),
        'post-bar': request.POST.get('bar'),
        'data': data,
    })


def view_with_argument(request, name):
    """A view that takes a string argument

    The purpose of this view is to check that if a space is provided in
    the argument, the test framework unescapes the %20 before passing
    the value to the view.
    """
    if name == 'Arthur Dent':
        return HttpResponse('Hi, Arthur')
    else:
        return HttpResponse('Howdy, %s' % name)


def nested_view(request):
    """
    A view that uses test client to call another view.
    """
    setup_test_environment()
    c = Client()
    c.get("/no_template_view/")
    return render(request, 'base.html', {'nested': 'yes'})


def login_protected_redirect_view(request):
    "A view that redirects all requests to the GET view"
    return HttpResponseRedirect('/get_view/')
login_protected_redirect_view = login_required(login_protected_redirect_view)


def redirect_to_self_with_changing_query_view(request):
    query = request.GET.copy()
    query['counter'] += '0'
    return HttpResponseRedirect('/redirect_to_self_with_changing_query_view/?%s' % urlencode(query))


def set_session_view(request):
    "A view that sets a session variable"
    request.session['session_var'] = 'YES'
    return HttpResponse('set_session')


def check_session_view(request):
    "A view that reads a session variable"
    return HttpResponse(request.session.get('session_var', 'NO'))


def request_methods_view(request):
    "A view that responds with the request method"
    return HttpResponse('request method: %s' % request.method)


def return_unicode(request):
    return render(request, 'unicode.html')


def return_undecodable_binary(request):
    return HttpResponse(
        b'%PDF-1.4\r\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document http://www.reportlab.com'
    )


def return_json_response(request):
    return JsonResponse({'key': 'value'})


def return_json_file(request):
    "A view that parses and returns a JSON string as a file."
    match = CONTENT_TYPE_RE.match(request.META['CONTENT_TYPE'])
    if match:
        charset = match.group(1)
    else:
        charset = settings.DEFAULT_CHARSET

    # This just checks that the uploaded data is JSON
    obj_dict = json.loads(request.body.decode(charset))
    obj_json = json.dumps(obj_dict, cls=DjangoJSONEncoder, ensure_ascii=False)
    response = HttpResponse(obj_json.encode(charset), status=200,
                            content_type='application/json; charset=%s' % charset)
    response['Content-Disposition'] = 'attachment; filename=testfile.json'
    return response


def check_headers(request):
    "A view that responds with value of the X-ARG-CHECK header"
    return HttpResponse('HTTP_X_ARG_CHECK: %s' % request.META.get('HTTP_X_ARG_CHECK', 'Undefined'))


def body(request):
    "A view that is requested with GET and accesses request.body. Refs #14753."
    return HttpResponse(request.body)


def read_all(request):
    "A view that is requested with accesses request.read()."
    return HttpResponse(request.read())


def read_buffer(request):
    "A view that is requested with accesses request.read(LARGE_BUFFER)."
    return HttpResponse(request.read(99999))


def request_context_view(request):
    # Special attribute that won't be present on a plain HttpRequest
    request.special_path = request.path
    return render(request, 'request_context.html')


def render_template_multiple_times(request):
    """A view that renders a template multiple times."""
    return HttpResponse(
        render_to_string('base.html') + render_to_string('base.html'))
