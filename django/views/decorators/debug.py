import functools

from django.utils.decorators import require_method_decorator


def sensitive_variables(*variables):
    """
    Indicate which variables used in the decorated function are sensitive so
    that those variables can later be treated in a special way, for example
    by hiding them when logging unhandled exceptions.

    Accept two forms:

    * with specified variable names:

        @sensitive_variables('user', 'password', 'credit_card')
        def my_function(user):
            password = user.pass_word
            credit_card = user.credit_card_number
            ...

    * without any specified variable names, in which case consider all
      variables are sensitive:

        @sensitive_variables()
        def my_function()
            ...
    """
    if len(variables) == 1 and callable(variables[0]):
        raise TypeError(
            'sensitive_variables() must be called to use it as a decorator, '
            'e.g., use @sensitive_variables(), not @sensitive_variables.'
        )

    def decorator(view_func):
        # The function name `sensitive_variables_wrapper` and arguments
        # `func_args` and `func_kwargs` are used by the debug view's
        # `get_traceback_frame_variables` and must not be changed.
        @functools.wraps(view_func)
        def sensitive_variables_wrapper(*func_args, **func_kwargs):
            # ensure `sensitive_variables_wrapper` is accessible in the current
            # frame's `f_locals`
            nonlocal sensitive_variables_wrapper
            return view_func(*func_args, **func_kwargs)
        sensitive_variables_wrapper.sensitive_variables = (
            variables or '__ALL__'
        )
        return sensitive_variables_wrapper
    return decorator


def sensitive_post_parameters(*parameters):
    """
    Indicate which POST parameters used in the decorated view are sensitive,
    so that those parameters can later be treated in a special way, for example
    by hiding them when logging unhandled exceptions.

    Accept two forms:

    * with specified parameters:

        @sensitive_post_parameters('password', 'credit_card')
        def my_view(request):
            pw = request.POST['password']
            cc = request.POST['credit_card']
            ...

    * without any specified parameters, in which case consider all
      variables are sensitive:

        @sensitive_post_parameters()
        def my_view(request)
            ...
    """
    if len(parameters) == 1 and callable(parameters[0]):
        raise TypeError(
            'sensitive_post_parameters() must be called to use it as a '
            'decorator, e.g., use @sensitive_post_parameters(), not '
            '@sensitive_post_parameters.'
        )

    if not parameters:
        parameters = '__ALL__'

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            require_method_decorator(request, 'sensitive_post_parameters')
            request.sensitive_post_parameters = parameters
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
