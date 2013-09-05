from xml.dom.minidom import parseString

from django.contrib.auth.decorators import login_required, permission_required
from django.core import mail
from django.forms import fields
from django.forms.forms import Form, ValidationError
from django.forms.formsets import formset_factory, BaseFormSet
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.template import Context, Template
from django.utils.decorators import method_decorator
from django.utils.six.moves.urllib.parse import urlencode

def get_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    t = Template('This is a test. {{ var }} is the value.', name='GET Template')
    c = Context({'var': request.GET.get('var', 42)})

    return HttpResponse(t.render(c))

def post_view(request):
    """A view that expects a POST, and returns a different template depending
    on whether any POST data is available
    """
    if request.method == 'POST':
        if request.POST:
            t = Template('Data received: {{ data }} is the value.', name='POST Template')
            c = Context({'data': request.POST['value']})
        else:
            t = Template('Viewing POST page.', name='Empty POST Template')
            c = Context()
    else:
        t = Template('Viewing GET page.', name='Empty GET Template')
        c = Context()

    return HttpResponse(t.render(c))

def view_with_header(request):
    "A view that has a custom header"
    response = HttpResponse()
    response['X-DJANGO-TEST'] = 'Slartibartfast'
    return response

def raw_post_view(request):
    """A view which expects raw XML to be posted and returns content extracted
    from the XML"""
    if request.method == 'POST':
        root = parseString(request.body)
        first_book = root.firstChild.firstChild
        title, author = [n.firstChild.nodeValue for n in first_book.childNodes]
        t = Template("{{ title }} - {{ author }}", name="Book template")
        c = Context({"title": title, "author": author})
    else:
        t = Template("GET request.", name="Book GET template")
        c = Context()

    return HttpResponse(t.render(c))

def redirect_view(request):
    "A view that redirects all requests to the GET view"
    if request.GET:
        query = '?' + urlencode(request.GET, True)
    else:
        query = ''
    return HttpResponseRedirect('/test_client/get_view/' + query)

def view_with_secure(request):
    "A view that indicates if the request was secure"
    response = HttpResponse()
    response.test_was_secure_request = request.is_secure()
    return response

def double_redirect_view(request):
    "A view that redirects all requests to a redirection view"
    return HttpResponseRedirect('/test_client/permanent_redirect_view/')

def bad_view(request):
    "A view that returns a 404 with some error content"
    return HttpResponseNotFound('Not found!. This page contains some MAGIC content')

TestChoices = (
    ('a', 'First Choice'),
    ('b', 'Second Choice'),
    ('c', 'Third Choice'),
    ('d', 'Fourth Choice'),
    ('e', 'Fifth Choice')
)

class TestForm(Form):
    text = fields.CharField()
    email = fields.EmailField()
    value = fields.IntegerField()
    single = fields.ChoiceField(choices=TestChoices)
    multi = fields.MultipleChoiceField(choices=TestChoices)

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get("text") == "Raise non-field error":
            raise ValidationError("Non-field error.")
        return cleaned_data

def form_view(request):
    "A view that tests a simple form"
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            t = Template('Valid POST data.', name='Valid POST Template')
            c = Context()
        else:
            t = Template('Invalid POST data. {{ form.errors }}', name='Invalid POST Template')
            c = Context({'form': form})
    else:
        form = TestForm(request.GET)
        t = Template('Viewing base form. {{ form }}.', name='Form GET Template')
        c = Context({'form': form})

    return HttpResponse(t.render(c))

def form_view_with_template(request):
    "A view that tests a simple form"
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            message = 'POST data OK'
        else:
            message = 'POST data has errors'
    else:
        form = TestForm()
        message = 'GET form page'
    return render_to_response('form_view.html',
        {
            'form': form,
            'message': message
        }
    )

class BaseTestFormSet(BaseFormSet):
    def clean(self):
        """Checks that no two email addresses are the same."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid
            return

        emails = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            email = form.cleaned_data['email']
            if email in emails:
                raise ValidationError(
                    "Forms in a set must have distinct email addresses."
                )
            emails.append(email)

TestFormSet = formset_factory(TestForm, BaseTestFormSet)

def formset_view(request):
    "A view that tests a simple formset"
    if request.method == 'POST':
        formset = TestFormSet(request.POST)
        if formset.is_valid():
            t = Template('Valid POST data.', name='Valid POST Template')
            c = Context()
        else:
            t = Template('Invalid POST data. {{ my_formset.errors }}',
                         name='Invalid POST Template')
            c = Context({'my_formset': formset})
    else:
        formset = TestForm(request.GET)
        t = Template('Viewing base formset. {{ my_formset }}.',
                     name='Formset GET Template')
        c = Context({'my_formset': formset})
    return HttpResponse(t.render(c))

def login_protected_view(request):
    "A simple view that is login protected."
    t = Template('This is a login protected test. Username is {{ user.username }}.', name='Login Template')
    c = Context({'user': request.user})

    return HttpResponse(t.render(c))
login_protected_view = login_required(login_protected_view)

def login_protected_view_changed_redirect(request):
    "A simple view that is login protected with a custom redirect field set"
    t = Template('This is a login protected test. Username is {{ user.username }}.', name='Login Template')
    c = Context({'user': request.user})

    return HttpResponse(t.render(c))
login_protected_view_changed_redirect = login_required(redirect_field_name="redirect_to")(login_protected_view_changed_redirect)

def _permission_protected_view(request):
    "A simple view that is permission protected."
    t = Template('This is a permission protected test. '
                 'Username is {{ user.username }}. '
                 'Permissions are {{ user.get_all_permissions }}.' ,
                 name='Permissions Template')
    c = Context({'user': request.user})
    return HttpResponse(t.render(c))
permission_protected_view = permission_required('permission_not_granted')(_permission_protected_view)
permission_protected_view_exception = permission_required('permission_not_granted', raise_exception=True)(_permission_protected_view)

class _ViewManager(object):
    @method_decorator(login_required)
    def login_protected_view(self, request):
        t = Template('This is a login protected test using a method. '
                     'Username is {{ user.username }}.',
                     name='Login Method Template')
        c = Context({'user': request.user})
        return HttpResponse(t.render(c))

    @method_decorator(permission_required('permission_not_granted'))
    def permission_protected_view(self, request):
        t = Template('This is a permission protected test using a method. '
                     'Username is {{ user.username }}. '
                     'Permissions are {{ user.get_all_permissions }}.' ,
                     name='Permissions Template')
        c = Context({'user': request.user})
        return HttpResponse(t.render(c))

_view_manager = _ViewManager()
login_protected_method_view = _view_manager.login_protected_view
permission_protected_method_view = _view_manager.permission_protected_view

def session_view(request):
    "A view that modifies the session"
    request.session['tobacconist'] = 'hovercraft'

    t = Template('This is a view that modifies the session.',
                 name='Session Modifying View Template')
    c = Context()
    return HttpResponse(t.render(c))

def broken_view(request):
    """A view which just raises an exception, simulating a broken view."""
    raise KeyError("Oops! Looks like you wrote some bad code.")

def mail_sending_view(request):
    mail.EmailMessage(
        "Test message",
        "This is a test email",
        "from@example.com",
        ['first@example.com', 'second@example.com']).send()
    return HttpResponse("Mail sent")

def mass_mail_sending_view(request):
    m1 = mail.EmailMessage(
        'First Test message',
        'This is the first test email',
        'from@example.com',
        ['first@example.com', 'second@example.com'])
    m2 = mail.EmailMessage(
        'Second Test message',
        'This is the second test email',
        'from@example.com',
        ['second@example.com', 'third@example.com'])

    c = mail.get_connection()
    c.send_messages([m1,m2])

    return HttpResponse("Mail sent")
