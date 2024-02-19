"""Parallel building utilities."""

from __future__ import annotations

import os
import time
import traceback
from math import sqrt
from typing import TYPE_CHECKING, Any, Callable

try:
    import multiprocessing
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False

from sphinx.errors import SphinxParallelError
from sphinx.util import logging

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# our parallel functionality only works for the forking Process
parallel_available = multiprocessing and os.name == 'posix'


class SerialTasks:
    """Has the same interface as ParallelTasks, but executes tasks directly."""

    def __init__(self, nproc: int = 1) -> None:
        pass

    def add_task(
        self, task_func: Callable, arg: Any = None, result_func: Callable | None = None,
    ) -> None:
        if arg is not None:
            res = task_func(arg)
        else:
            res = task_func()
        if result_func:
            result_func(res)

    def join(self) -> None:
        pass


class ParallelTasks:
    """Executes *nproc* tasks in parallel after forking."""

    def __init__(self, nproc: int) -> None:
        self.nproc = nproc
        # (optional) function performed by each task on the result of main task
        self._result_funcs: dict[int, Callable] = {}
        # task arguments
        self._args: dict[int, list[Any] | None] = {}
        # list of subprocesses (both started and waiting)
        self._procs: dict[int, Any] = {}
        # list of receiving pipe connections of running subprocesses
        self._precvs: dict[int, Any] = {}
        # list of receiving pipe connections of waiting subprocesses
        self._precvsWaiting: dict[int, Any] = {}
        # number of working subprocesses
        self._pworking = 0
        # task number of each subprocess
        self._taskid = 0

    def _process(self, pipe: Any, func: Callable, arg: Any) -> None:
        try:
            collector = logging.LogCollector()
            with collector.collect():
                if arg is None:
                    ret = func()
                else:
                    ret = func(arg)
            failed = False
        except BaseException as err:
            failed = True
            errmsg = traceback.format_exception_only(err.__class__, err)[0].strip()
            ret = (errmsg, traceback.format_exc())
        logging.convert_serializable(collector.logs)
        pipe.send((failed, collector.logs, ret))

    def add_task(
        self, task_func: Callable, arg: Any = None, result_func: Callable | None = None,
    ) -> None:
        tid = self._taskid
        self._taskid += 1
        self._result_funcs[tid] = result_func or (lambda arg, result: None)
        self._args[tid] = arg
        precv, psend = multiprocessing.Pipe(False)
        context: Any = multiprocessing.get_context('fork')
        proc = context.Process(target=self._process, args=(psend, task_func, arg))
        self._procs[tid] = proc
        self._precvsWaiting[tid] = precv
        self._join_one()

    def join(self) -> None:
        try:
            while self._pworking:
                if not self._join_one():
                    time.sleep(0.02)
        finally:
            # shutdown other child processes on failure
            self.terminate()

    def terminate(self) -> None:
        for tid in list(self._precvs):
            self._procs[tid].terminate()
            self._result_funcs.pop(tid)
            self._procs.pop(tid)
            self._precvs.pop(tid)
            self._pworking -= 1

    def _join_one(self) -> bool:
        joined_any = False
        for tid, pipe in self._precvs.items():
            if pipe.poll():
                exc, logs, result = pipe.recv()
                if exc:
                    raise SphinxParallelError(*result)
                for log in logs:
                    logger.handle(log)
                self._result_funcs.pop(tid)(self._args.pop(tid), result)
                self._procs[tid].join()
                self._precvs.pop(tid)
                self._pworking -= 1
                joined_any = True
                break

        while self._precvsWaiting and self._pworking < self.nproc:
            newtid, newprecv = self._precvsWaiting.popitem()
            self._precvs[newtid] = newprecv
            self._procs[newtid].start()
            self._pworking += 1

        return joined_any


def make_chunks(arguments: Sequence[str], nproc: int, maxbatch: int = 10) -> list[Any]:
    # determine how many documents to read in one go
    nargs = len(arguments)
    chunksize = nargs // nproc
    if chunksize >= maxbatch:
        # try to improve batch size vs. number of batches
        chunksize = int(sqrt(nargs / nproc * maxbatch))
    if chunksize == 0:
        chunksize = 1
    nchunks, rest = divmod(nargs, chunksize)
    if rest:
        nchunks += 1
    # partition documents in "chunks" that will be written by one Process
    return [arguments[i * chunksize:(i + 1) * chunksize] for i in range(nchunks)]
