import json
import warnings

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponse, HttpResponseRedirect,
                         HttpResponseServerError, HttpResponseNotFound,)
from django.shortcuts import render_to_response
from django.core.serializers.json import DjangoJSONEncoder
from django.template import RequestContext
from django.test import Client
from django.test.client import CONTENT_TYPE_RE
from django.test.utils import setup_test_environment


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

    # request.REQUEST is deprecated, but needs testing until removed.
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        request_foo = request.REQUEST.get('foo')
        request_bar = request.REQUEST.get('bar')

    return render_to_response(template, {
        'get-foo': request.GET.get('foo'),
        'get-bar': request.GET.get('bar'),
        'post-foo': request.POST.get('foo'),
        'post-bar': request.POST.get('bar'),
        'request-foo': request_foo,
        'request-bar': request_bar,
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
    c.get("/test_client_regress/no_template_view")
    return render_to_response('base.html', {'nested': 'yes'})


def login_protected_redirect_view(request):
    "A view that redirects all requests to the GET view"
    return HttpResponseRedirect('/test_client_regress/get_view/')
login_protected_redirect_view = login_required(login_protected_redirect_view)

def no_broken_links_view(request):
    return HttpResponse(
    """
    Lots of html stuff, including a few local links:
      <a href="/test_client_regress/get_view/">here</a>
      <a href="/test_client_regress/get_view">This should redirect to add the /</a>
      <a some="attribute" href="/test_client_regress/no_template_view/">
        a redirect view. Doesn't matter if closing tag missing.

    Some external links:
      <a href="http://djangoproject.com/weblog/">Django blog</a>

    Some anchor links should be ignored, such as:
      <a href="mailto:me@example.com">Send me an email</a>, or
      <a href="ftp://example.com">Download from here</a>

    Including a <a lats of bad="stuff" href="http://djangoproject.com">Missing slash</a>
    Whole bunch of other stuff before the page ends.
    """
    )

def broken_external_link_view(request):
    return HttpResponse(
    """
    Lots of html stuff, including a few local links:
      <a href="/test_client_regress/get_view/">here</a>
      <a href="/test_client_regress/get_view">This should redirect to add the /</a>
      <a some="attribute" href="/test_client_regress/no_template_view/">
        a redirect view. Doesn't matter if closing tag missing.

    Some external links:
      <a class="this one's fine" href="http://djangoproject.com/weblog">Django blog</a>
    But this one's a
      <a href="http://djangoproject.com/badlink.html">Broken link</a>
    Whole bunch of other stuff before the page ends.
    """
    )

def broken_internal_link_view(request):
    return HttpResponse(
    """
    Lots of html stuff, including a few local links:

      <a class="test" href="/test_client_regress/broken_view/">A broken view</a>

    """
    )

def broken_redirected_link_view(request):
    return HttpResponse(
    """
    Lots of html stuff, including a few local links:

      <a class="test" href="/test_client_regress/broken_view">A broken
      redirected view</a>

    """
    )

def bad_internal_link_view(request):
    return HttpResponse(
    """
    Lots of html stuff, including a few local links:

      <a class="test" href="/test_client_regress/bad_view/">A bad view</a>

    """
    )

def blank_link_view(request):
    return HttpResponse(
    """
    If a link uses the url template tag to create the link for the href like
    this:
     href="{% url my-url-name arg %}"
    and fails, it will end up with blank href="", this would be useful to
    catch!

      <a class="test" href="">A blank link.</a>

    """
    )

def internal_page_link_view(request):
    return HttpResponse(
    """
    A link which is just internal to the page, href="#content" needs to
    have a matching element with an id="content" on the page.

      <a class="test" href="#content">This one should be fine</a>

      <a href="#">This one should be ignored (lots of JS uses)</a>

      <a href="#footer">But this one isn't valid</a> as there's no corresponding
      element with the id="footer"

      <div id="content">
        Here's the content
      </div>
    """
    )

def broken_view(request):
    return HttpResponseServerError()

def bad_view(request):
    return HttpResponseNotFound()

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
    return render_to_response('unicode.html')


def return_undecodable_binary(request):
    return HttpResponse(
        b'%PDF-1.4\r\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document http://www.reportlab.com'
    )


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
    return render_to_response('request_context.html', context_instance=RequestContext(request, {}))
