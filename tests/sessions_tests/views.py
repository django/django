from django.http import Http404


def session_modify_and_http404(request):
    request.session['foo'] = 'bar'
    raise Http404
