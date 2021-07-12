import random
from string import ascii_letters, digits

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from .forms import CreatePaste, DeletePaste
from .models import Paste


def index(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreatePaste(request.POST)
        if form.is_valid():
            key = ''.join([random.SystemRandom().choice(ascii_letters + digits) for _ in range(16)])
            paste = Paste(
                key=key,
                code=form.cleaned_data.get('code')
            )
            paste.save()
            return redirect('view', key=key)
    else:
        form = CreatePaste()
    return render(
        request=request,
        template_name='pastebin/create.html',
        context={
            'form': form
        }
    )


def view(request: HttpRequest, key: str) -> HttpResponse:
    if not Paste.objects.filter(key=key).first():
        return render(
            request=request,
            template_name='pastebin/status/not_found.html',
            context={
                'key': key
            }
        )
    # If the client is CURL
    if str(request.META.get('HTTP_USER_AGENT')).lower().startswith('curl'):
        return HttpResponse(
            content_type='text/plain',
            content=Paste.objects.filter(key=key).first().code
        )
    # If the paste got deleted
    if request.method == 'POST':
        form = DeletePaste(request.POST)
        if form.is_valid():
            Paste.objects.filter(key=key).first().delete()
            return render(
                request=request,
                template_name='pastebin/status/deleted.html'
            )
    else:
        form = DeletePaste()
    return render(
        request=request,
        template_name='pastebin/view.html',
        context={
            'form': form,
            'code': Paste.objects.filter(key=key).first().code,
        }
    )
