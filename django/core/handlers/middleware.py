class MiddlewareMixin(object):
    def __init__(self, get_response=None):
        self.get_response = get_response
        super(MiddlewareMixin, self).__init__()

    def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            try:
                response = self.get_response(request)
            except Exception as e:
                if hasattr(self, 'process_exception'):
                    return self.process_exception(request, e)
                else:
                    raise
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response
