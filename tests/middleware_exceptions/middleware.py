from django.http import Http404, HttpResponse
from django.template import engines
from django.template.response import TemplateResponse

log = []


class BaseMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class ProcessExceptionMiddleware(BaseMiddleware):
    def process_exception(self, request, exception):
        return HttpResponse('Exception caught')


class ProcessExceptionLogMiddleware(BaseMiddleware):
    def process_exception(self, request, exception):
        log.append('process-exception')


class ProcessExceptionExcMiddleware(BaseMiddleware):
    def process_exception(self, request, exception):
        raise Exception('from process-exception')


class ProcessViewMiddleware(BaseMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        return HttpResponse('Processed view %s' % view_func.__name__)


class ProcessViewNoneMiddleware(BaseMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        log.append('processed view %s' % view_func.__name__)
        return None


class ProcessViewTemplateResponseMiddleware(BaseMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        template = engines['django'].from_string('Processed view {{ view }}{% for m in mw %}\n{{ m }}{% endfor %}')
        return TemplateResponse(request, template, {'mw': [self.__class__.__name__], 'view': view_func.__name__})


class TemplateResponseMiddleware(BaseMiddleware):
    def process_template_response(self, request, response):
        response.context_data['mw'].append(self.__class__.__name__)
        return response


class LogMiddleware(BaseMiddleware):
    def __call__(self, request):
        response = self.get_response(request)
        log.append((response.status_code, response.content))
        return response


class NotFoundMiddleware(BaseMiddleware):
    def __call__(self, request):
        raise Http404('not found')
