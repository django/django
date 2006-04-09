"""Error types for dispatcher mechanism
"""

class DispatcherError(Exception):
	"""Base class for all Dispatcher errors"""
class DispatcherKeyError(KeyError, DispatcherError):
	"""Error raised when unknown (sender,signal) set specified"""
class DispatcherTypeError(TypeError, DispatcherError):
	"""Error raised when inappropriate signal-type specified (None)"""

