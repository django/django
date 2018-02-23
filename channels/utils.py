import asyncio
import types
from concurrent.futures import CancelledError


def name_that_thing(thing):
    """
    Returns either the function/class path or just the object's repr
    """
    # Instance method
    if hasattr(thing, "im_class"):
        # Mocks will recurse im_class forever
        if hasattr(thing, "mock_calls"):
            return "<mock>"
        return name_that_thing(thing.im_class) + "." + thing.im_func.func_name
    # Other named thing
    if hasattr(thing, "__name__"):
        if hasattr(thing, "__class__") and not isinstance(thing, (types.FunctionType, types.MethodType)):
            if thing.__class__ is not type and not issubclass(thing.__class__, type):
                return name_that_thing(thing.__class__)
        if hasattr(thing, "__self__"):
            return "%s.%s" % (thing.__self__.__module__, thing.__self__.__name__)
        if hasattr(thing, "__module__"):
            return "%s.%s" % (thing.__module__, thing.__name__)
    # Generic instance of a class
    if hasattr(thing, "__class__"):
        return name_that_thing(thing.__class__)
    return repr(thing)


async def await_many_dispatch(consumer_callables, dispatch):
    """
    Given a set of consumer callables, awaits on them all and passes results
    from them to the dispatch awaitable as they come in.
    """
    # Start them all off as tasks
    loop = asyncio.get_event_loop()
    tasks = [
        loop.create_task(consumer_callable())
        for consumer_callable in consumer_callables
    ]
    try:
        while True:
            # Wait for any of them to complete
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # Find the completed one(s), yield results, and replace them
            for i, task in enumerate(tasks):
                if task.done():
                    result = task.result()
                    await dispatch(result)
                    tasks[i] = asyncio.ensure_future(consumer_callables[i]())
    finally:
        # Make sure we clean up tasks on exit
        for task in tasks:
            task.cancel()
            try:
                await task
            except CancelledError:
                pass
