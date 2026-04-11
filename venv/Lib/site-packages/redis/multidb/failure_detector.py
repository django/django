import math
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Type

from typing_extensions import Optional

from redis.multidb.circuit import State as CBState

DEFAULT_MIN_NUM_FAILURES = 1000
DEFAULT_FAILURE_RATE_THRESHOLD = 0.1
DEFAULT_FAILURES_DETECTION_WINDOW = 2


class FailureDetector(ABC):
    @abstractmethod
    def register_failure(self, exception: Exception, cmd: tuple) -> None:
        """Register a failure that occurred during command execution."""
        pass

    @abstractmethod
    def register_command_execution(self, cmd: tuple) -> None:
        """Register a command execution."""
        pass

    @abstractmethod
    def set_command_executor(self, command_executor) -> None:
        """Set the command executor for this failure."""
        pass


class CommandFailureDetector(FailureDetector):
    """
    Detects a failure based on a threshold of failed commands during a specific period of time.
    """

    def __init__(
        self,
        min_num_failures: int = DEFAULT_MIN_NUM_FAILURES,
        failure_rate_threshold: float = DEFAULT_FAILURE_RATE_THRESHOLD,
        failure_detection_window: float = DEFAULT_FAILURES_DETECTION_WINDOW,
        error_types: Optional[List[Type[Exception]]] = None,
    ) -> None:
        """
        Initialize a new CommandFailureDetector instance.

        Args:
            min_num_failures: Minimal count of failures required for failover
            failure_rate_threshold: Percentage of failures required for failover
            failure_detection_window: Time interval for executing health checks.
            error_types: Optional list of exception types to trigger failover. If None, all exceptions are counted.

        The detector tracks command failures within a sliding time window. When the number of failures
        exceeds the threshold within the specified duration, it triggers failure detection.
        """
        self._command_executor = None
        self._min_num_failures = min_num_failures
        self._failure_rate_threshold = failure_rate_threshold
        self._failure_detection_window = failure_detection_window
        self._error_types = error_types
        self._commands_executed: int = 0
        self._start_time: datetime = datetime.now()
        self._end_time: datetime = self._start_time + timedelta(
            seconds=self._failure_detection_window
        )
        self._failures_count: int = 0
        self._lock = threading.RLock()

    def register_failure(self, exception: Exception, cmd: tuple) -> None:
        with self._lock:
            if self._error_types:
                if type(exception) in self._error_types:
                    self._failures_count += 1
            else:
                self._failures_count += 1

            self._check_threshold()

    def set_command_executor(self, command_executor) -> None:
        self._command_executor = command_executor

    def register_command_execution(self, cmd: tuple) -> None:
        with self._lock:
            if not self._start_time < datetime.now() < self._end_time:
                self._reset()

            self._commands_executed += 1

    def _check_threshold(self):
        if self._failures_count >= self._min_num_failures and self._failures_count >= (
            math.ceil(self._commands_executed * self._failure_rate_threshold)
        ):
            self._command_executor.active_database.circuit.state = CBState.OPEN
            self._reset()

    def _reset(self) -> None:
        with self._lock:
            self._start_time = datetime.now()
            self._end_time = self._start_time + timedelta(
                seconds=self._failure_detection_window
            )
            self._failures_count = 0
            self._commands_executed = 0
