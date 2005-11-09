class TemplateDebugMiddleware(object):
    def linebreak_iter(self, template_source):
        import re
        newline_re = re.compile("^", re.M)
        for match in newline_re.finditer(template_source):
            yield match.start()
        yield len(template_source) + 1
            
    def process_exception(self, request, exception):
        from django.core.template.loader import render_to_string
        from django.utils.html import escape
        from django.utils.httpwrappers import HttpResponseServerError
        from django.core.extensions import DjangoContext
        from itertools import count, izip
        
        context_lines = 10
        if hasattr(exception, 'source'):
            origin, (start, end) = exception.source
            template_source = origin.reload()
            
           
           
            line = 0
            upto = 0
            source_lines = []
            linebreaks = izip(count(0), self.linebreak_iter(template_source))
            linebreaks.next() # skip the nothing before initial line start
            for num, next in linebreaks:
                if start >= upto and end <= next :
                    line = num
                    before = escape(template_source[upto:start])
                    during = escape(template_source[start:end])
                    after = escape(template_source[end:next - 1])
                
                source_lines.append( (num, escape(template_source[upto:next - 1])) )
                upto = next
                
            total = len(source_lines)
            
            top = max(0, line - context_lines)
            bottom = min(total, line + 1 + context_lines)
            traceback = hasattr(exception, 'traceback') and exception.traceback or ''
            result = render_to_string('template_debug',
                       DjangoContext(request, {
                           'message'      : exception.args[0], 
                           'traceback'    : traceback,
                           'source_lines' : source_lines[top:bottom],
                           'before' : before, 
                           'during': during,
                           'after': after,
                           'top': top ,
                           'bottom': bottom ,
                           'total' : total,
                           'line'  : line,
                           'name' : origin.name,
                        }),
                        )
            return HttpResponseServerError(result)
