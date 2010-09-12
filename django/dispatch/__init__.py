"""Multi-consumer multi-producer dispatching mechanism

Originally based on pydispatch (BSD) http://pypi.python.org/pypi/PyDispatcher/2.0.1
See license.txt for original license.

Heavily modified for Django's purposes.
"""

from django.dispatch.dispatcher import Signal, receiver