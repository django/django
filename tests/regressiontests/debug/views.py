from regressiontests.debug import BrokenException, except_args

def view_exception(request, n):
    raise BrokenException(except_args[int(n)])

