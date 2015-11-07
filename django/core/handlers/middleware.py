class MiddlewareMixin(object):
    def __call__(self, request, response_factory):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            response = response_factory(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response
