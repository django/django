class TemplateDebugMiddleware(object):
    def process_exception(self, request, exception):
        from django.core.template.loader import render_to_string
        from django.utils.html import escape
        from django.utils.httpwrappers import HttpResponseServerError
        from django.core.extensions import DjangoContext
        from itertools import count, izip
        context_lines = 10
        if hasattr(exception, 'source'):
            origin, line = exception.source
            template_source = origin.reload()
            
            source_lines = [ (i,s) for (i,s) in  izip(count(1), escape(template_source).split("\n"))]
            total = len(source_lines)
            top = max(0, line - context_lines)
            bottom = min(total, line + 1 + context_lines)
            traceback = hasattr(exception, 'traceback') and exception.traceback or ''
            return HttpResponseServerError(
                    render_to_string('template_debug',
                           DjangoContext(request, {
                               'message'      : exception.args[0], 
                               'traceback'    : traceback,
                               'source_lines' : source_lines[top:bottom],
                               'top': top ,
                               'bottom': bottom ,
                               'total' : total,
                               'line'  : line
                            }),
                            )
                    )