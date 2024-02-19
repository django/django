import asyncio
import logging
import time
import traceback

from .compatibility import guarantee_single_callable

logger = logging.getLogger(__name__)


class StatelessServer:
    """
    Base server class that handles basic concepts like application instance
    creation/pooling, exception handling, and similar, for stateless protocols
    (i.e. ones without actual incoming connections to the process)

    Your code should override the handle() method, doing whatever it needs to,
    and calling get_or_create_application_instance with a unique `scope_id`
    and `scope` for the scope it wants to get.

    If an application instance is found with the same `scope_id`, you are
    given its input queue, otherwise one is made for you with the scope provided
    and you are given that fresh new input queue. Either way, you should do
    something like:

    input_queue = self.get_or_create_application_instance(
        "user-123456",
        {"type": "testprotocol", "user_id": "123456", "username": "andrew"},
    )
    input_queue.put_nowait(message)

    If you try and create an application instance and there are already
    `max_application` instances, the oldest/least recently used one will be
    reclaimed and shut down to make space.

    Application coroutines that error will be found periodically (every 100ms
    by default) and have their exceptions printed to the console. Override
    application_exception() if you want to do more when this happens.

    If you override run(), make sure you handle things like launching the
    application checker.
    """

    application_checker_interval = 0.1

    def __init__(self, application, max_applications=1000):
        # Parameters
        self.application = application
        self.max_applications = max_applications
        # Initialisation
        self.application_instances = {}

    ### Mainloop and handling

    def run(self):
        """
        Runs the asyncio event loop with our handler loop.
        """
        event_loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.application_checker())
        try:
            event_loop.run_until_complete(self.handle())
        except KeyboardInterrupt:
            logger.info("Exiting due to Ctrl-C/interrupt")

    async def handle(self):
        raise NotImplementedError("You must implement handle()")

    async def application_send(self, scope, message):
        """
        Receives outbound sends from applications and handles them.
        """
        raise NotImplementedError("You must implement application_send()")

    ### Application instance management

    def get_or_create_application_instance(self, scope_id, scope):
        """
        Creates an application instance and returns its queue.
        """
        if scope_id in self.application_instances:
            self.application_instances[scope_id]["last_used"] = time.time()
            return self.application_instances[scope_id]["input_queue"]
        # See if we need to delete an old one
        while len(self.application_instances) > self.max_applications:
            self.delete_oldest_application_instance()
        # Make an instance of the application
        input_queue = asyncio.Queue()
        application_instance = guarantee_single_callable(self.application)
        # Run it, and stash the future for later checking
        future = asyncio.ensure_future(
            application_instance(
                scope=scope,
                receive=input_queue.get,
                send=lambda message: self.application_send(scope, message),
            ),
        )
        self.application_instances[scope_id] = {
            "input_queue": input_queue,
            "future": future,
            "scope": scope,
            "last_used": time.time(),
        }
        return input_queue

    def delete_oldest_application_instance(self):
        """
        Finds and deletes the oldest application instance
        """
        oldest_time = min(
            details["last_used"] for details in self.application_instances.values()
        )
        for scope_id, details in self.application_instances.items():
            if details["last_used"] == oldest_time:
                self.delete_application_instance(scope_id)
                # Return to make sure we only delete one in case two have
                # the same oldest time
                return

    def delete_application_instance(self, scope_id):
        """
        Removes an application instance (makes sure its task is stopped,
        then removes it from the current set)
        """
        details = self.application_instances[scope_id]
        del self.application_instances[scope_id]
        if not details["future"].done():
            details["future"].cancel()

    async def application_checker(self):
        """
        Goes through the set of current application instance Futures and cleans up
        any that are done/prints exceptions for any that errored.
        """
        while True:
            await asyncio.sleep(self.application_checker_interval)
            for scope_id, details in list(self.application_instances.items()):
                if details["future"].done():
                    exception = details["future"].exception()
                    if exception:
                        await self.application_exception(exception, details)
                    try:
                        del self.application_instances[scope_id]
                    except KeyError:
                        # Exception handling might have already got here before us. That's fine.
                        pass

    async def application_exception(self, exception, application_details):
        """
        Called whenever an application coroutine has an exception.
        """
        logging.error(
            "Exception inside application: %s\n%s%s",
            exception,
            "".join(traceback.format_tb(exception.__traceback__)),
            f"  {exception}",
        )
