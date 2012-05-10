from django.core.exceptions import ImproperlyConfigured

class ScriptnameMiddleware(object):
    
    def __init__(self, handler, scriptname):
        self.handler = handler
        if not scriptname.startswith('/'):
            scriptname = '/' + scriptname
        if scriptname.endswith('/'):
            scriptname = scriptname[:-1]
        print 'scriptname:', scriptname
        self.scriptname = scriptname
    
    def __call__(self, environ, start_response):
        if environ.get('SCRIPT_NAME', ''):
            raise ImproperlyConfigured('Only use with manage.py!')
        
        path_info = environ.get('PATH_INFO', '')
        if not path_info.startswith(self.scriptname+'/'):
            start_response('302 Found', [
                ('Location', (self.scriptname+('' if path_info.startswith('/') else '/')+path_info)),
                ('Content-Length', '0'),
            ])
            return ''
        
        environ['PATH_INFO'] = path_info[len(self.scriptname):]
        environ['SCRIPT_NAME'] = self.scriptname
        return self.handler(environ, start_response)