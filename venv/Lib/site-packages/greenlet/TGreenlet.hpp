#ifndef GREENLET_GREENLET_HPP
#define GREENLET_GREENLET_HPP
/*
 * Declarations of the core data structures.
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "greenlet_compiler_compat.hpp"
#include "greenlet_refs.hpp"
#include "greenlet_cpython_compat.hpp"
#include "greenlet_allocator.hpp"

using greenlet::refs::OwnedObject;
using greenlet::refs::OwnedGreenlet;
using greenlet::refs::OwnedMainGreenlet;
using greenlet::refs::BorrowedGreenlet;

#if PY_VERSION_HEX < 0x30B00A6
#  define _PyCFrame CFrame
#  define _PyInterpreterFrame _interpreter_frame
#endif

#if GREENLET_PY312
#  define Py_BUILD_CORE
#  include "internal/pycore_frame.h"
#endif

#if GREENLET_PY314
#  include "internal/pycore_interpframe_structs.h"
#if defined(_MSC_VER) || defined(__MINGW64__)
#   include "greenlet_msvc_compat.hpp"
#else
#  include "internal/pycore_interpframe.h"
#endif
#ifdef Py_GIL_DISABLED
#   include "internal/pycore_tstate.h"
#endif
#endif

// XXX: TODO: Work to remove all virtual functions
// for speed of calling and size of objects (no vtable).
// One pattern is the Curiously Recurring Template
namespace greenlet
{
    class ExceptionState
    {
    private:
        G_NO_COPIES_OF_CLS(ExceptionState);

        // Even though these are borrowed objects, we actually own
        // them, when they're not null.
        // XXX: Express that in the API.
    private:
        _PyErr_StackItem* exc_info;
        _PyErr_StackItem exc_state;
    public:
        ExceptionState();
        void operator<<(const PyThreadState *const tstate) noexcept;
        void operator>>(PyThreadState* tstate) noexcept;
        void clear() noexcept;

        int tp_traverse(visitproc visit, void* arg) noexcept;
        void tp_clear() noexcept;
    };

    template<typename T>
    void operator<<(const PyThreadState *const tstate, T& exc);

    class PythonStateContext
    {
    protected:
        greenlet::refs::OwnedContext _context;
    public:
        inline const greenlet::refs::OwnedContext& context() const
        {
            return this->_context;
        }
        inline greenlet::refs::OwnedContext& context()
        {
            return this->_context;
        }

        inline void tp_clear()
        {
            this->_context.CLEAR();
        }

        template<typename T>
        inline static PyObject* context(T* tstate)
        {
            return tstate->context;
        }

        template<typename T>
        inline static void context(T* tstate, PyObject* new_context)
        {
            tstate->context = new_context;
            tstate->context_ver++;
        }
    };
    class SwitchingArgs;
    class PythonState : public PythonStateContext
    {
    public:
        typedef greenlet::refs::OwnedReference<struct _frame> OwnedFrame;
    private:
        G_NO_COPIES_OF_CLS(PythonState);
        // We own this if we're suspended (although currently we don't
        // tp_traverse into it; that's a TODO). If we're running, it's
        // empty. If we get deallocated and *still* have a frame, it
        // won't be reachable from the place that normally decref's
        // it, so we need to do it (hence owning it).
        OwnedFrame _top_frame;
#if GREENLET_USE_CFRAME
        _PyCFrame* cframe;
        int use_tracing;
#endif
#if GREENLET_PY314
        int py_recursion_depth;
        // I think this is only used by the JIT. At least,
        // we only got errors not switching it when the JIT was enabled.
        //    Python/generated_cases.c.h:12469: _PyEval_EvalFrameDefault:
        //      Assertion `tstate->current_executor == NULL' failed.
        // see https://github.com/python-greenlet/greenlet/issues/460
        PyObject* current_executor;
        _PyStackRef* stackpointer;
    #ifdef Py_GIL_DISABLED
        _PyCStackRef* c_stack_refs;
    #endif
#elif GREENLET_PY312
        int py_recursion_depth;
        int c_recursion_depth;
#else
        int recursion_depth;
#endif
#if GREENLET_PY313
        PyObject *delete_later;
#else
        int trash_delete_nesting;
#endif
#if GREENLET_PY311
        _PyInterpreterFrame* current_frame;
        _PyStackChunk* datastack_chunk;
        PyObject** datastack_top;
        PyObject** datastack_limit;
#endif
        // The PyInterpreterFrame list on 3.12+ contains some entries that are
        // on the C stack, which can't be directly accessed while a greenlet is
        // suspended. In order to keep greenlet gr_frame introspection working,
        // we adjust stack switching to rewrite the interpreter frame list
        // to skip these C-stack frames; we call this "exposing" the greenlet's
        // frames because it makes them valid to work with in Python. Then when
        // the greenlet is resumed we need to remember to reverse the operation
        // we did. The C-stack frames are "entry frames" which are a low-level
        // interpreter detail; they're not needed for introspection, but do
        // need to be present for the eval loop to work.
        void unexpose_frames();

    public:

        PythonState();
        // You can use this for testing whether we have a frame
        // or not. It returns const so they can't modify it.
        const OwnedFrame& top_frame() const noexcept;

        inline void operator<<(const PyThreadState *const tstate) noexcept;
        inline void operator>>(PyThreadState* tstate) noexcept;
        void clear() noexcept;

        int tp_traverse(visitproc visit, void* arg, bool visit_top_frame) noexcept;
        void tp_clear(bool own_top_frame) noexcept;
        void set_initial_state(const PyThreadState* const tstate) noexcept;
#if GREENLET_USE_CFRAME
        void set_new_cframe(_PyCFrame& frame) noexcept;
#endif

        void may_switch_away() noexcept;
        inline void will_switch_from(PyThreadState *const origin_tstate) noexcept;
        void did_finish(PyThreadState* tstate) noexcept;
    };

    class StackState
    {
        // By having only plain C (POD) members, no virtual functions
        // or bases, we get a trivial assignment operator generated
        // for us. However, that's not safe since we do manage memory.
        // So we declare an assignment operator that only works if we
        // don't have any memory allocated. (We don't use
        // std::shared_ptr for reference counting just to keep this
        // object small)
    private:
        char* _stack_start;
        char* stack_stop;
        char* stack_copy;
        intptr_t _stack_saved;
        StackState* stack_prev;
        inline int copy_stack_to_heap_up_to(const char* const stop) noexcept;
        inline void free_stack_copy() noexcept;

    public:
        /**
         * Creates a started, but inactive, state, using *current*
         * as the previous.
         */
        StackState(void* mark, StackState& current);
        /**
         * Creates an inactive, unstarted, state.
         */
        StackState();
        ~StackState();
        StackState(const StackState& other);
        StackState& operator=(const StackState& other);
        inline void copy_heap_to_stack(const StackState& current) noexcept;
        inline int copy_stack_to_heap(char* const stackref, const StackState& current) noexcept;
        inline bool started() const noexcept;
        inline bool main() const noexcept;
        inline bool active() const noexcept;
        inline void set_active() noexcept;
        inline void set_inactive() noexcept;
        inline intptr_t stack_saved() const noexcept;
        inline char* stack_start() const noexcept;
        static inline StackState make_main() noexcept;
#ifdef GREENLET_USE_STDIO
        friend std::ostream& operator<<(std::ostream& os, const StackState& s);
#endif

        // Fill in [dest, dest + n) with the values that would be at
        // [src, src + n) while this greenlet is running. This is like memcpy
        // except that if the greenlet is suspended it accounts for the portion
        // of the greenlet's stack that was spilled to the heap. `src` may
        // be on this greenlet's stack, or on the heap, but not on a different
        // greenlet's stack.
        void copy_from_stack(void* dest, const void* src, size_t n) const;
    };
#ifdef GREENLET_USE_STDIO
    std::ostream& operator<<(std::ostream& os, const StackState& s);
#endif

    class SwitchingArgs
    {
    private:
        G_NO_ASSIGNMENT_OF_CLS(SwitchingArgs);
        // If args and kwargs are both false (NULL), this is a *throw*, not a
        // switch. PyErr_... must have been called already.
        OwnedObject _args;
        OwnedObject _kwargs;
    public:

        SwitchingArgs()
        {}

        SwitchingArgs(const OwnedObject& args, const OwnedObject& kwargs)
            : _args(args),
              _kwargs(kwargs)
        {}

        SwitchingArgs(const SwitchingArgs& other)
            : _args(other._args),
              _kwargs(other._kwargs)
        {}

        const OwnedObject& args()
        {
            return this->_args;
        }

        const OwnedObject& kwargs()
        {
            return this->_kwargs;
        }

        /**
         * Moves ownership from the argument to this object.
         */
        SwitchingArgs& operator<<=(SwitchingArgs& other)
        {
            if (this != &other) {
                this->_args = other._args;
                this->_kwargs = other._kwargs;
                other.CLEAR();
            }
            return *this;
        }

        /**
         * Acquires ownership of the argument (consumes the reference).
         */
        SwitchingArgs& operator<<=(PyObject* args)
        {
            this->_args = OwnedObject::consuming(args);
            this->_kwargs.CLEAR();
            return *this;
        }

        /**
         * Acquires ownership of the argument.
         *
         * Sets the args to be the given value; clears the kwargs.
         */
        SwitchingArgs& operator<<=(OwnedObject& args)
        {
            assert(&args != &this->_args);
            this->_args = args;
            this->_kwargs.CLEAR();
            args.CLEAR();

            return *this;
        }

        explicit operator bool() const noexcept
        {
            return this->_args || this->_kwargs;
        }

        inline void CLEAR()
        {
            this->_args.CLEAR();
            this->_kwargs.CLEAR();
        }

        const std::string as_str() const noexcept
        {
            return PyUnicode_AsUTF8(
                OwnedObject::consuming(
                    PyUnicode_FromFormat(
                        "SwitchingArgs(args=%R, kwargs=%R)",
                        this->_args.borrow(),
                        this->_kwargs.borrow()
                    )
                ).borrow()
            );
        }
    };

    class ThreadState;

    class UserGreenlet;
    class MainGreenlet;

    class Greenlet
    {
    private:
        G_NO_COPIES_OF_CLS(Greenlet);
        PyGreenlet* const _self;
    private:
        // XXX: Work to remove these.
        friend class ThreadState;
        friend class UserGreenlet;
        friend class MainGreenlet;
    protected:
        ExceptionState exception_state;
        SwitchingArgs switch_args;
        StackState stack_state;
        PythonState python_state;
        Greenlet(PyGreenlet* p, const StackState& initial_state);
    public:
        // This constructor takes ownership of the PyGreenlet, by
        // setting ``p->pimpl = this;``.
        Greenlet(PyGreenlet* p);
        virtual ~Greenlet();

        const OwnedObject context() const;

        // You MUST call this _very_ early in the switching process to
        // prepare anything that may need prepared. This might perform
        // garbage collections or otherwise run arbitrary Python code.
        //
        // One specific use of it is for Python 3.11+, preventing
        // running arbitrary code at unsafe times. See
        // PythonState::may_switch_away().
        inline void may_switch_away()
        {
            this->python_state.may_switch_away();
        }

        inline void context(refs::BorrowedObject new_context);

        inline SwitchingArgs& args()
        {
            return this->switch_args;
        }

        virtual const refs::BorrowedMainGreenlet main_greenlet() const = 0;

        inline intptr_t stack_saved() const noexcept
        {
            return this->stack_state.stack_saved();
        }

        // This is used by the macro SLP_SAVE_STATE to compute the
        // difference in stack sizes. It might be nice to handle the
        // computation ourself, but the type of the result
        // varies by platform, so doing it in the macro is the
        // simplest way.
        inline const char* stack_start() const noexcept
        {
            return this->stack_state.stack_start();
        }

        virtual OwnedObject throw_GreenletExit_during_dealloc(const ThreadState& current_thread_state);
        virtual OwnedObject g_switch() = 0;
        /**
         * Force the greenlet to appear dead. Used when it's not
         * possible to throw an exception into a greenlet anymore.
         *
         * This losses access to the thread state and the main greenlet.
         */
        virtual void murder_in_place();

        /**
         * Called when somebody notices we were running in a dead
         * thread to allow cleaning up resources (because we can't
         * raise GreenletExit into it anymore).
         * This is very similar to ``murder_in_place()``, except that
         * it DOES NOT lose the main greenlet or thread state.
         */
        inline void deactivate_and_free();


        // Called when some thread wants to deallocate a greenlet
        // object.
        // The thread may or may not be the same thread the greenlet
        // was running in.
        // The thread state will be null if the thread the greenlet
        // was running in was known to have exited.
        void deallocing_greenlet_in_thread(const ThreadState* current_state);

        // Must be called on 3.12+ before exposing a suspended greenlet's
        // frames to user code. This rewrites the linked list of interpreter
        // frames to skip the ones that are being stored on the C stack (which
        // can't be safely accessed while the greenlet is suspended because
        // that stack space might be hosting a different greenlet), and
        // sets PythonState::frames_were_exposed so we remember to restore
        // the original list before resuming the greenlet. The C-stack frames
        // are a low-level interpreter implementation detail; while they're
        // important to the bytecode eval loop, they're superfluous for
        // introspection purposes.
        void expose_frames();


        // TODO: Figure out how to make these non-public.
        inline void slp_restore_state() noexcept;
        inline int slp_save_state(char *const stackref) noexcept;

        inline bool is_currently_running_in_some_thread() const;
        virtual bool belongs_to_thread(const ThreadState* state) const;

        inline bool started() const
        {
            return this->stack_state.started();
        }
        inline bool active() const
        {
            return this->stack_state.active();
        }
        inline bool main() const
        {
            return this->stack_state.main();
        }
        virtual refs::BorrowedMainGreenlet find_main_greenlet_in_lineage() const = 0;

        virtual const OwnedGreenlet parent() const = 0;
        virtual void parent(const refs::BorrowedObject new_parent) = 0;

        inline const PythonState::OwnedFrame& top_frame()
        {
            return this->python_state.top_frame();
        }

        virtual const OwnedObject& run() const = 0;
        virtual void run(const refs::BorrowedObject nrun) = 0;


        virtual int tp_traverse(visitproc visit, void* arg);
        virtual int tp_clear();


        // Return the thread state that the greenlet is running in, or
        // null if the greenlet is not running or the thread is known
        // to have exited.
        virtual ThreadState* thread_state() const noexcept = 0;

        // Return true if the greenlet is known to have been running
        // (active) in a thread that has now exited.
        virtual bool was_running_in_dead_thread() const noexcept = 0;

        // Return a borrowed greenlet that is the Python object
        // this object represents.
        inline BorrowedGreenlet self() const noexcept
        {
            return BorrowedGreenlet(this->_self);
        }

        // For testing. If this returns true, we should pretend that
        // slp_switch() failed.
        virtual bool force_slp_switch_error() const noexcept;

    protected:
        inline void release_args();

        // The functions that must not be inlined are declared virtual.
        // We also mark them as protected, not private, so that the
        // compiler is forced to call them through a function pointer.
        // (A sufficiently smart compiler could directly call a private
        // virtual function since it can never be overridden in a
        // subclass).

        // Also TODO: Switch away from integer error codes and to enums,
        // or throw exceptions when possible.
        struct switchstack_result_t
        {
            int status;
            Greenlet* the_new_current_greenlet;
            OwnedGreenlet origin_greenlet;

            switchstack_result_t()
                : status(0),
                  the_new_current_greenlet(nullptr)
            {}

            switchstack_result_t(int err)
                : status(err),
                  the_new_current_greenlet(nullptr)
            {}

            switchstack_result_t(int err, Greenlet* state, OwnedGreenlet& origin)
                : status(err),
                  the_new_current_greenlet(state),
                  origin_greenlet(origin)
            {
            }

            switchstack_result_t(int err, Greenlet* state, const BorrowedGreenlet& origin)
                : status(err),
                  the_new_current_greenlet(state),
                  origin_greenlet(origin)
            {
            }

            switchstack_result_t(const switchstack_result_t& other)
                : status(other.status),
                  the_new_current_greenlet(other.the_new_current_greenlet),
                  origin_greenlet(other.origin_greenlet)
            {}

            switchstack_result_t& operator=(const switchstack_result_t& other)
            {
                this->status = other.status;
                this->the_new_current_greenlet = other.the_new_current_greenlet;
                this->origin_greenlet = other.origin_greenlet;
                return *this;
            }
        };

        OwnedObject on_switchstack_or_initialstub_failure(
            Greenlet* target,
            const switchstack_result_t& err,
            const bool target_was_me=false,
            const bool was_initial_stub=false);

        // Returns the previous greenlet we just switched away from.
        virtual OwnedGreenlet g_switchstack_success() noexcept;


        // Check the preconditions for switching to this greenlet; if they
        // aren't met, throws PyErrOccurred. Most callers will want to
        // catch this and clear the arguments
        inline void check_switch_allowed() const;
        class GreenletStartedWhileInPython : public std::runtime_error
        {
        public:
            GreenletStartedWhileInPython() : std::runtime_error("")
            {}
        };

    protected:


        /**
           Perform a stack switch into this greenlet.

           This temporarily sets the global variable
           ``switching_thread_state`` to this greenlet; as soon as the
           call to ``slp_switch`` completes, this is reset to NULL.
           Consequently, this depends on the GIL.

           TODO: Adopt the stackman model and pass ``slp_switch`` a
           callback function and context pointer; this eliminates the
           need for global variables altogether.

           Because the stack switch happens in this function, this
           function can't use its own stack (local) variables, set
           before the switch, and then accessed after the switch.

           Further, you con't even access ``g_thread_state_global``
           before and after the switch from the global variable.
           Because it is thread local some compilers cache it in a
           register/on the stack, notably new versions of MSVC; this
           breaks with strange crashes sometime later, because writing
           to anything in ``g_thread_state_global`` after the switch
           is actually writing to random memory. For this reason, we
           call a non-inlined function to finish the operation. (XXX:
           The ``/GT`` MSVC compiler argument probably fixes that.)

           It is very important that stack switch is 'atomic', i.e. no
           calls into other Python code allowed (except very few that
           are safe), because global variables are very fragile. (This
           should no longer be the case with thread-local variables.)

        */
        // Made virtual to facilitate subclassing UserGreenlet for testing.
        virtual switchstack_result_t g_switchstack(void);

class TracingGuard
{
private:
    PyThreadState* tstate;
public:
    TracingGuard()
        : tstate(PyThreadState_GET())
    {
        PyThreadState_EnterTracing(this->tstate);
    }

    ~TracingGuard()
    {
        PyThreadState_LeaveTracing(this->tstate);
        this->tstate = nullptr;
    }

    inline void CallTraceFunction(const OwnedObject& tracefunc,
                                  const greenlet::refs::ImmortalEventName& event,
                                  const BorrowedGreenlet& origin,
                                  const BorrowedGreenlet& target)
    {
        // TODO: This calls tracefunc(event, (origin, target)). Add a shortcut
        // function for that that's specialized to avoid the Py_BuildValue
        // string parsing, or start with just using "ON" format with PyTuple_Pack(2,
        // origin, target). That seems like what the N format is meant
        // for.
        // XXX: Why does event not automatically cast back to a PyObject?
        // It tries to call the "deleted constructor ImmortalEventName
        // const" instead.
        assert(tracefunc);
        assert(event);
        assert(origin);
        assert(target);
        greenlet::refs::NewReference retval(
            PyObject_CallFunction(
                tracefunc.borrow(),
                "O(OO)",
                event.borrow(),
                origin.borrow(),
                target.borrow()
            ));
        if (!retval) {
            throw PyErrOccurred::from_current();
        }
    }
};

      static void
      g_calltrace(const OwnedObject& tracefunc,
                  const greenlet::refs::ImmortalEventName& event,
                  const greenlet::refs::BorrowedGreenlet& origin,
                  const BorrowedGreenlet& target);
    private:
        OwnedObject g_switch_finish(const switchstack_result_t& err);

    };

    class UserGreenlet : public Greenlet
    {
    private:
        static greenlet::PythonAllocator<UserGreenlet> allocator;
        OwnedMainGreenlet _main_greenlet;
        OwnedObject _run_callable;
        OwnedGreenlet _parent;
    public:
        static void* operator new(size_t UNUSED(count));
        static void operator delete(void* ptr);

        UserGreenlet(PyGreenlet* p, BorrowedGreenlet the_parent);
        virtual ~UserGreenlet();

        virtual refs::BorrowedMainGreenlet find_main_greenlet_in_lineage() const;
        virtual bool was_running_in_dead_thread() const noexcept;
        virtual ThreadState* thread_state() const noexcept;
        virtual OwnedObject g_switch();
        virtual const OwnedObject& run() const
        {
            if (this->started() || !this->_run_callable) {
                throw AttributeError("run");
            }
            return this->_run_callable;
        }
        virtual void run(const refs::BorrowedObject nrun);

        virtual const OwnedGreenlet parent() const;
        virtual void parent(const refs::BorrowedObject new_parent);

        virtual const refs::BorrowedMainGreenlet main_greenlet() const;

        virtual void murder_in_place();
        virtual bool belongs_to_thread(const ThreadState* state) const;
        virtual int tp_traverse(visitproc visit, void* arg);
        virtual int tp_clear();
        class ParentIsCurrentGuard
        {
        private:
            OwnedGreenlet oldparent;
            UserGreenlet* greenlet;
            G_NO_COPIES_OF_CLS(ParentIsCurrentGuard);
        public:
            ParentIsCurrentGuard(UserGreenlet* p, const ThreadState& thread_state);
            ~ParentIsCurrentGuard();
        };
        virtual OwnedObject throw_GreenletExit_during_dealloc(const ThreadState& current_thread_state);
    protected:
        virtual switchstack_result_t g_initialstub(void* mark);
    private:
        // This function isn't meant to return.
        // This accepts raw pointers and the ownership of them at the
        // same time. The caller should use ``inner_bootstrap(origin.relinquish_ownership())``.
        void inner_bootstrap(PyGreenlet* origin_greenlet, PyObject* run);
    };

    class BrokenGreenlet : public UserGreenlet
    {
    private:
        static greenlet::PythonAllocator<BrokenGreenlet> allocator;
    public:
        bool _force_switch_error = false;
        bool _force_slp_switch_error = false;

        static void* operator new(size_t UNUSED(count));
        static void operator delete(void* ptr);
        BrokenGreenlet(PyGreenlet* p, BorrowedGreenlet the_parent)
            : UserGreenlet(p, the_parent)
        {}
        virtual ~BrokenGreenlet()
        {}

        virtual switchstack_result_t g_switchstack(void);
        virtual bool force_slp_switch_error() const noexcept;

    };

    class MainGreenlet : public Greenlet
    {
    private:
        static greenlet::PythonAllocator<MainGreenlet> allocator;
        refs::BorrowedMainGreenlet _self;
        ThreadState* _thread_state;
        G_NO_COPIES_OF_CLS(MainGreenlet);
    public:
        static void* operator new(size_t UNUSED(count));
        static void operator delete(void* ptr);

        MainGreenlet(refs::BorrowedMainGreenlet::PyType*, ThreadState*);
        virtual ~MainGreenlet();


        virtual const OwnedObject& run() const;
        virtual void run(const refs::BorrowedObject nrun);

        virtual const OwnedGreenlet parent() const;
        virtual void parent(const refs::BorrowedObject new_parent);

        virtual const refs::BorrowedMainGreenlet main_greenlet() const;

        virtual refs::BorrowedMainGreenlet find_main_greenlet_in_lineage() const;
        virtual bool was_running_in_dead_thread() const noexcept;
        virtual ThreadState* thread_state() const noexcept;
        void thread_state(ThreadState*) noexcept;
        virtual OwnedObject g_switch();
        virtual int tp_traverse(visitproc visit, void* arg);
    };

    // Instantiate one on the stack to save the GC state,
    // and then disable GC. When it goes out of scope, GC will be
    // restored to its original state. Sadly, these APIs are only
    // available on 3.10+; luckily, we only need them on 3.11+.
#if GREENLET_PY310
    class GCDisabledGuard
    {
    private:
        int was_enabled = 0;
    public:
        GCDisabledGuard()
            : was_enabled(PyGC_IsEnabled())
        {
            PyGC_Disable();
        }

        ~GCDisabledGuard()
        {
            if (this->was_enabled) {
                PyGC_Enable();
            }
        }
    };
#endif

    OwnedObject& operator<<=(OwnedObject& lhs, greenlet::SwitchingArgs& rhs) noexcept;

    //TODO: Greenlet::g_switch() should call this automatically on its
    //return value. As it is, the module code is calling it.
    static inline OwnedObject
    single_result(const OwnedObject& results)
    {
        if (results
            && PyTuple_Check(results.borrow())
            && PyTuple_GET_SIZE(results.borrow()) == 1) {
            PyObject* result = PyTuple_GET_ITEM(results.borrow(), 0);
            assert(result);
            return OwnedObject::owning(result);
        }
        return results;
    }


    static OwnedObject
    g_handle_exit(const OwnedObject& greenlet_result);


    template<typename T>
    void operator<<(const PyThreadState *const lhs, T& rhs)
    {
        rhs.operator<<(lhs);
    }

} // namespace greenlet ;

#endif
