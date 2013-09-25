import functools

from django.http import HttpRequest


def sensitive_variables(*variables):
    """
    Indicates which variables used in the decorated function are sensitive, so
    that those variables can later be treated in a special way, for example
    by hiding them when logging unhandled exceptions.

    Two forms are accepted:

    * with specified variable names:

        @sensitive_variables('user', 'password', 'credit_card')
        def my_function(user):
            password = user.pass_word
            credit_card = user.credit_card_number
            ...

    * without any specified variable names, in which case it is assumed that
      all variables are considered sensitive:

        @sensitive_variables()
        def my_function()
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def sensitive_variables_wrapper(*func_args, **func_kwargs):
            if variables:
                sensitive_variables_wrapper.sensitive_variables = variables
            else:
                sensitive_variables_wrapper.sensitive_variables = '__ALL__'
            return func(*func_args, **func_kwargs)
        return sensitive_variables_wrapper
    return decorator


def sensitive_post_parameters(*parameters):
    """
    Indicates which POST parameters used in the decorated view are sensitive,
    so that those parameters can later be treated in a special way, for example
    by hiding them when logging unhandled exceptions.

    Two forms are accepted:

    * with specified parameters:

        @sensitive_post_parameters('password', 'credit_card')
        def my_view(request):
            pw = request.POST['password']
            cc = request.POST['credit_card']
            ...

    * without any specified parameters, in which case it is assumed that
      all parameters are considered sensitive:

        @sensitive_post_parameters()
        def my_view(request)
            ...
    """
    def decorator(view):
        @functools.wraps(view)
        def sensitive_post_parameters_wrapper(request, *args, **kwargs):
            assert isinstance(request, HttpRequest), (
              "sensitive_post_parameters didn't receive an HttpRequest. If you "
              "are decorating a classmethod, be sure to use @method_decorator."
            )
            if parameters:
                request.sensitive_post_parameters = parameters
            else:
                request.sensitive_post_parameters = '__ALL__'
            return view(request, *args, **kwargs)
        return sensitive_post_parameters_wrapper
    return decorator
