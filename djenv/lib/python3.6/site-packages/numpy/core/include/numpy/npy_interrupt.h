
/* Signal handling:

This header file defines macros that allow your code to handle
interrupts received during processing.  Interrupts that
could reasonably be handled:

SIGINT, SIGABRT, SIGALRM, SIGSEGV

****Warning***************

Do not allow code that creates temporary memory or increases reference
counts of Python objects to be interrupted unless you handle it
differently.

**************************

The mechanism for handling interrupts is conceptually simple:

  - replace the signal handler with our own home-grown version
     and store the old one.
  - run the code to be interrupted -- if an interrupt occurs
     the handler should basically just cause a return to the
     calling function for finish work.
  - restore the old signal handler

Of course, every code that allows interrupts must account for
returning via the interrupt and handle clean-up correctly.  But,
even still, the simple paradigm is complicated by at least three
factors.

 1) platform portability (i.e. Microsoft says not to use longjmp
     to return from signal handling.  They have a __try  and __except
     extension to C instead but what about mingw?).

 2) how to handle threads: apparently whether signals are delivered to
    every thread of the process or the "invoking" thread is platform
    dependent. --- we don't handle threads for now.

 3) do we need to worry about re-entrance.  For now, assume the
    code will not call-back into itself.

Ideas:

 1) Start by implementing an approach that works on platforms that
    can use setjmp and longjmp functionality and does nothing
    on other platforms.

 2) Ignore threads --- i.e. do not mix interrupt handling and threads

 3) Add a default signal_handler function to the C-API but have the rest
    use macros.


Simple Interface:


In your C-extension: around a block of code you want to be interruptible
with a SIGINT

NPY_SIGINT_ON
[code]
NPY_SIGINT_OFF

In order for this to work correctly, the
[code] block must not allocate any memory or alter the reference count of any
Python objects.  In other words [code] must be interruptible so that continuation
after NPY_SIGINT_OFF will only be "missing some computations"

Interrupt handling does not work well with threads.

*/

/* Add signal handling macros
   Make the global variable and signal handler part of the C-API
*/

#ifndef NPY_INTERRUPT_H
#define NPY_INTERRUPT_H

#ifndef NPY_NO_SIGNAL

#include <setjmp.h>
#include <signal.h>

#ifndef sigsetjmp

#define NPY_SIGSETJMP(arg1, arg2) setjmp(arg1)
#define NPY_SIGLONGJMP(arg1, arg2) longjmp(arg1, arg2)
#define NPY_SIGJMP_BUF jmp_buf

#else

#define NPY_SIGSETJMP(arg1, arg2) sigsetjmp(arg1, arg2)
#define NPY_SIGLONGJMP(arg1, arg2) siglongjmp(arg1, arg2)
#define NPY_SIGJMP_BUF sigjmp_buf

#endif

#    define NPY_SIGINT_ON {                                             \
                   PyOS_sighandler_t _npy_sig_save;                     \
                   _npy_sig_save = PyOS_setsig(SIGINT, _PyArray_SigintHandler); \
                   if (NPY_SIGSETJMP(*((NPY_SIGJMP_BUF *)_PyArray_GetSigintBuf()), \
                                 1) == 0) {                             \

#    define NPY_SIGINT_OFF }                                      \
        PyOS_setsig(SIGINT, _npy_sig_save);                       \
        }

#else /* NPY_NO_SIGNAL  */

#define NPY_SIGINT_ON
#define NPY_SIGINT_OFF

#endif /* HAVE_SIGSETJMP */

#endif /* NPY_INTERRUPT_H */
