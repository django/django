from django.utils import httpwrappers
from django.utils.translation import check_for_language

def set_language(request):
    """
    Redirect to a given url while setting the chosen language in the
    session or cookie. The url and the language code need to be
    specified in the GET paramters.
    """
    lang_code = request.GET['language']
    next = request.GET.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = httpwrappers.HttpResponseRedirect(next)
    if check_for_language(lang_code):
        if hasattr(request, 'session'):
            request.session['django_language'] = lang_code
        else:
            response.set_cookie('django_language', lang_code)
    return response
