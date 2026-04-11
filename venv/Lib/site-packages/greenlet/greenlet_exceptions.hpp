#ifndef GREENLET_EXCEPTIONS_HPP
#define GREENLET_EXCEPTIONS_HPP

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdexcept>
#include <string>

#ifdef __clang__
#    pragma clang diagnostic push
#    pragma clang diagnostic ignored "-Wunused-function"
#endif

namespace greenlet {

    class PyErrOccurred : public std::runtime_error
    {
    public:

        // CAUTION: In debug builds, may run arbitrary Python code.
        static const PyErrOccurred
        from_current()
        {
            assert(PyErr_Occurred());
#ifndef NDEBUG
            // This is not exception safe, and
            // not necessarily safe in general (what if it switches?)
            // But we only do this in debug mode, where we are in
            // tight control of what exceptions are getting raised and
            // can prevent those issues.

            // You can't call PyObject_Str with a pending exception.
            PyObject* typ;
            PyObject* val;
            PyObject* tb;

            PyErr_Fetch(&typ, &val, &tb);
            PyObject* typs = PyObject_Str(typ);
            PyObject* vals = PyObject_Str(val ? val : typ);
            const char* typ_msg = PyUnicode_AsUTF8(typs);
            const char* val_msg = PyUnicode_AsUTF8(vals);
            PyErr_Restore(typ, val, tb);

            std::string msg(typ_msg);
            msg += ": ";
            msg += val_msg;
            PyErrOccurred ex(msg);
            Py_XDECREF(typs);
            Py_XDECREF(vals);

            return ex;
#else
            return PyErrOccurred();
#endif
        }

        PyErrOccurred() : std::runtime_error("")
        {
            assert(PyErr_Occurred());
        }

        PyErrOccurred(const std::string& msg) : std::runtime_error(msg)
        {
            assert(PyErr_Occurred());
        }

        PyErrOccurred(PyObject* exc_kind, const char* const msg)
            : std::runtime_error(msg)
        {
            PyErr_SetString(exc_kind, msg);
        }

        PyErrOccurred(PyObject* exc_kind, const std::string msg)
            : std::runtime_error(msg)
        {
            // This copies the c_str, so we don't have any lifetime
            // issues to worry about.
            PyErr_SetString(exc_kind, msg.c_str());
        }

        PyErrOccurred(PyObject* exc_kind,
                      const std::string msg, //This is the format
                                             //string; that's not
                                             //usually safe!

                      PyObject* borrowed_obj_one, PyObject* borrowed_obj_two)
            : std::runtime_error(msg)
        {

            //This is designed specifically for the
            //``check_switch_allowed`` function.

            // PyObject_Str and PyObject_Repr are safe to call with
            // NULL pointers; they return the string "<NULL>" in that
            // case.
            // This function always returns null.
            PyErr_Format(exc_kind,
                         msg.c_str(),
                         borrowed_obj_one, borrowed_obj_two);
        }
    };

    class TypeError : public PyErrOccurred
    {
    public:
        TypeError(const char* const what)
            : PyErrOccurred(PyExc_TypeError, what)
        {
        }
        TypeError(const std::string what)
            : PyErrOccurred(PyExc_TypeError, what)
        {
        }
    };

    class ValueError : public PyErrOccurred
    {
    public:
        ValueError(const char* const what)
            : PyErrOccurred(PyExc_ValueError, what)
        {
        }
    };

    class AttributeError : public PyErrOccurred
    {
    public:
        AttributeError(const char* const what)
            : PyErrOccurred(PyExc_AttributeError, what)
        {
        }
    };

    /**
     * Calls `Py_FatalError` when constructed, so you can't actually
     * throw this. It just makes static analysis easier.
     */
    class PyFatalError : public std::runtime_error
    {
    public:
        PyFatalError(const char* const msg)
            : std::runtime_error(msg)
        {
            Py_FatalError(msg);
        }
    };

    static inline PyObject*
    Require(PyObject* p, const std::string& msg="")
    {
        if (!p) {
            throw PyErrOccurred(msg);
        }
        return p;
    };

    static inline void
    Require(const int retval)
    {
        if (retval < 0) {
            throw PyErrOccurred();
        }
    };


};
#ifdef __clang__
#    pragma clang diagnostic pop
#endif

#endif
