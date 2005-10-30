from django.core.extensions import render_to_response
from django.utils.html import escape

context_lines = 10

class TemplateDebugMiddleware(object):
    def process_exception(self, request, exception):
        if hasattr(exception, 'source'):
            origin, line = exception.source
            template_source = origin.reload()
            
            source_lines = [ (i + 1,s) for (i,s) in  enumerate(escape(template_source).split("\n"))]
            total = len(source_lines)
            top = max(0, line - context_lines)
            bottom = min(total, line + 1 + context_lines)
       
            return render_to_response('template_debug', {
               'message'      : exception.args[0], 
               'source_lines' : source_lines[top:bottom],
               'top': top ,
               'bottom': bottom ,
               'total' : total,
               'line'  : line
            })
           