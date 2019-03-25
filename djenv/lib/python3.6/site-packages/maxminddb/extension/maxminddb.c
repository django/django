#include <Python.h>
#include <maxminddb.h>
#include "structmember.h"

#define __STDC_FORMAT_MACROS
#include <inttypes.h>

static PyTypeObject Reader_Type;
static PyTypeObject Metadata_Type;
static PyObject *MaxMindDB_error;

typedef struct {
    PyObject_HEAD               /* no semicolon */
    MMDB_s *mmdb;
    PyObject *closed;
} Reader_obj;

typedef struct {
    PyObject_HEAD               /* no semicolon */
    PyObject *binary_format_major_version;
    PyObject *binary_format_minor_version;
    PyObject *build_epoch;
    PyObject *database_type;
    PyObject *description;
    PyObject *ip_version;
    PyObject *languages;
    PyObject *node_count;
    PyObject *record_size;
} Metadata_obj;

static PyObject *from_entry_data_list(MMDB_entry_data_list_s **entry_data_list);
static PyObject *from_map(MMDB_entry_data_list_s **entry_data_list);
static PyObject *from_array(MMDB_entry_data_list_s **entry_data_list);
static PyObject *from_uint128(const MMDB_entry_data_list_s *entry_data_list);

#if PY_MAJOR_VERSION >= 3
    #define MOD_INIT(name) PyMODINIT_FUNC PyInit_ ## name(void)
    #define RETURN_MOD_INIT(m) return (m)
    #define FILE_NOT_FOUND_ERROR PyExc_FileNotFoundError
#else
    #define MOD_INIT(name) PyMODINIT_FUNC init ## name(void)
    #define RETURN_MOD_INIT(m) return
    #define PyInt_FromLong PyLong_FromLong
    #define FILE_NOT_FOUND_ERROR PyExc_IOError
#endif

#ifdef __GNUC__
    #  define UNUSED(x) UNUSED_ ## x __attribute__((__unused__))
#else
    #  define UNUSED(x) UNUSED_ ## x
#endif

static int Reader_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    char *filename;
    int mode = 0;

    static char *kwlist[] = {"database", "mode", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s|i", kwlist, &filename, &mode)) {
        return -1;
    }

    if (mode != 0 && mode != 1) {
        PyErr_Format(PyExc_ValueError, "Unsupported open mode (%i). Only "
            "MODE_AUTO and MODE_MMAP_EXT are supported by this extension.",
            mode);
        return -1;
    }

    if (0 != access(filename, R_OK)) {
        PyErr_Format(FILE_NOT_FOUND_ERROR,
                     "No such file or directory: '%s'",
                     filename);
        return -1;
    }

    MMDB_s *mmdb = (MMDB_s *)malloc(sizeof(MMDB_s));
    if (NULL == mmdb) {
        PyErr_NoMemory();
        return -1;
    }

    Reader_obj *mmdb_obj = (Reader_obj *)self;
    if (!mmdb_obj) {
        free(mmdb);
        PyErr_NoMemory();
        return -1;
    }

    uint16_t status = MMDB_open(filename, MMDB_MODE_MMAP, mmdb);

    if (MMDB_SUCCESS != status) {
        free(mmdb);
        PyErr_Format(
            MaxMindDB_error,
            "Error opening database file (%s). Is this a valid MaxMind DB file?",
            filename
            );
        return -1;
    }

    mmdb_obj->mmdb = mmdb;
    mmdb_obj->closed = Py_False;
    return 0;
}

static PyObject *Reader_get(PyObject *self, PyObject *args)
{
    char *ip_address = NULL;

    Reader_obj *mmdb_obj = (Reader_obj *)self;
    if (!PyArg_ParseTuple(args, "s", &ip_address)) {
        return NULL;
    }

    MMDB_s *mmdb = mmdb_obj->mmdb;

    if (NULL == mmdb) {
        PyErr_SetString(PyExc_ValueError,
                        "Attempt to read from a closed MaxMind DB.");
        return NULL;
    }

    int gai_error = 0;
    int mmdb_error = MMDB_SUCCESS;
    MMDB_lookup_result_s result =
        MMDB_lookup_string(mmdb, ip_address, &gai_error,
                           &mmdb_error);

    if (0 != gai_error) {
        PyErr_Format(PyExc_ValueError,
                     "'%s' does not appear to be an IPv4 or IPv6 address.",
                     ip_address);
        return NULL;
    }

    if (MMDB_SUCCESS != mmdb_error) {
        PyObject *exception;
        if (MMDB_IPV6_LOOKUP_IN_IPV4_DATABASE_ERROR == mmdb_error) {
            exception = PyExc_ValueError;
        } else {
            exception = MaxMindDB_error;
        }
        PyErr_Format(exception, "Error looking up %s. %s",
                     ip_address, MMDB_strerror(mmdb_error));
        return NULL;
    }

    if (!result.found_entry) {
        Py_RETURN_NONE;
    }

    MMDB_entry_data_list_s *entry_data_list = NULL;
    int status = MMDB_get_entry_data_list(&result.entry, &entry_data_list);
    if (MMDB_SUCCESS != status) {
        PyErr_Format(MaxMindDB_error,
                     "Error while looking up data for %s. %s",
                     ip_address, MMDB_strerror(status));
        MMDB_free_entry_data_list(entry_data_list);
        return NULL;
    }

    MMDB_entry_data_list_s *original_entry_data_list = entry_data_list;
    PyObject *py_obj = from_entry_data_list(&entry_data_list);
    MMDB_free_entry_data_list(original_entry_data_list);
    return py_obj;
}

static PyObject *Reader_metadata(PyObject *self, PyObject *UNUSED(args))
{
    Reader_obj *mmdb_obj = (Reader_obj *)self;

    if (NULL == mmdb_obj->mmdb) {
        PyErr_SetString(PyExc_IOError,
                        "Attempt to read from a closed MaxMind DB.");
        return NULL;
    }

    MMDB_entry_data_list_s *entry_data_list;
    MMDB_get_metadata_as_entry_data_list(mmdb_obj->mmdb, &entry_data_list);
    MMDB_entry_data_list_s *original_entry_data_list = entry_data_list;

    PyObject *metadata_dict = from_entry_data_list(&entry_data_list);
    MMDB_free_entry_data_list(original_entry_data_list);
    if (NULL == metadata_dict || !PyDict_Check(metadata_dict)) {
        PyErr_SetString(MaxMindDB_error,
                        "Error decoding metadata.");
        return NULL;
    }

    PyObject *args = PyTuple_New(0);
    if (NULL == args) {
        Py_DECREF(metadata_dict);
        return NULL;
    }

    PyObject *metadata = PyObject_Call((PyObject *)&Metadata_Type, args,
                                       metadata_dict);

    Py_DECREF(metadata_dict);
    return metadata;
}

static PyObject *Reader_close(PyObject *self, PyObject *UNUSED(args))
{
    Reader_obj *mmdb_obj = (Reader_obj *)self;

    if (NULL != mmdb_obj->mmdb) {
        MMDB_close(mmdb_obj->mmdb);
        free(mmdb_obj->mmdb);
        mmdb_obj->mmdb = NULL;
    }

    mmdb_obj->closed = Py_True;

    Py_RETURN_NONE;
}

static PyObject *Reader__enter__(PyObject *self, PyObject *UNUSED(args))
{
    Reader_obj *mmdb_obj = (Reader_obj *)self;

    if(mmdb_obj->closed == Py_True) {
        PyErr_SetString(PyExc_ValueError,
                        "Attempt to reopen a closed MaxMind DB.");
        return NULL;
    }

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *Reader__exit__(PyObject *self, PyObject *UNUSED(args))
{
    Reader_close(self, NULL);
    Py_RETURN_NONE;
}

static void Reader_dealloc(PyObject *self)
{
    Reader_obj *obj = (Reader_obj *)self;
    if (NULL != obj->mmdb) {
        Reader_close(self, NULL);
    }

    PyObject_Del(self);
}

static int Metadata_init(PyObject *self, PyObject *args, PyObject *kwds)
{

    PyObject
    *binary_format_major_version,
    *binary_format_minor_version,
    *build_epoch,
    *database_type,
    *description,
    *ip_version,
    *languages,
    *node_count,
    *record_size;

    static char *kwlist[] = {
        "binary_format_major_version",
        "binary_format_minor_version",
        "build_epoch",
        "database_type",
        "description",
        "ip_version",
        "languages",
        "node_count",
        "record_size",
        NULL
    };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOOOOOOOO", kwlist,
                                     &binary_format_major_version,
                                     &binary_format_minor_version,
                                     &build_epoch,
                                     &database_type,
                                     &description,
                                     &ip_version,
                                     &languages,
                                     &node_count,
                                     &record_size)) {
        return -1;
    }

    Metadata_obj *obj = (Metadata_obj *)self;

    obj->binary_format_major_version = binary_format_major_version;
    obj->binary_format_minor_version = binary_format_minor_version;
    obj->build_epoch = build_epoch;
    obj->database_type = database_type;
    obj->description = description;
    obj->ip_version = ip_version;
    obj->languages = languages;
    obj->node_count = node_count;
    obj->record_size = record_size;

    Py_INCREF(obj->binary_format_major_version);
    Py_INCREF(obj->binary_format_minor_version);
    Py_INCREF(obj->build_epoch);
    Py_INCREF(obj->database_type);
    Py_INCREF(obj->description);
    Py_INCREF(obj->ip_version);
    Py_INCREF(obj->languages);
    Py_INCREF(obj->node_count);
    Py_INCREF(obj->record_size);

    return 0;
}

static void Metadata_dealloc(PyObject *self)
{
    Metadata_obj *obj = (Metadata_obj *)self;
    Py_DECREF(obj->binary_format_major_version);
    Py_DECREF(obj->binary_format_minor_version);
    Py_DECREF(obj->build_epoch);
    Py_DECREF(obj->database_type);
    Py_DECREF(obj->description);
    Py_DECREF(obj->ip_version);
    Py_DECREF(obj->languages);
    Py_DECREF(obj->node_count);
    Py_DECREF(obj->record_size);
    PyObject_Del(self);
}

static PyObject *from_entry_data_list(MMDB_entry_data_list_s **entry_data_list)
{
    if (NULL == entry_data_list || NULL == *entry_data_list) {
        PyErr_SetString(
            MaxMindDB_error,
            "Error while looking up data. Your database may be corrupt or you have found a bug in libmaxminddb."
            );
        return NULL;
    }

    switch ((*entry_data_list)->entry_data.type) {
    case MMDB_DATA_TYPE_MAP:
        return from_map(entry_data_list);
    case MMDB_DATA_TYPE_ARRAY:
        return from_array(entry_data_list);
    case MMDB_DATA_TYPE_UTF8_STRING:
        return PyUnicode_FromStringAndSize(
                   (*entry_data_list)->entry_data.utf8_string,
                   (*entry_data_list)->entry_data.data_size
                   );
    case MMDB_DATA_TYPE_BYTES:
        return PyByteArray_FromStringAndSize(
                   (const char *)(*entry_data_list)->entry_data.bytes,
                   (Py_ssize_t)(*entry_data_list)->entry_data.data_size);
    case MMDB_DATA_TYPE_DOUBLE:
        return PyFloat_FromDouble((*entry_data_list)->entry_data.double_value);
    case MMDB_DATA_TYPE_FLOAT:
        return PyFloat_FromDouble((*entry_data_list)->entry_data.float_value);
    case MMDB_DATA_TYPE_UINT16:
        return PyLong_FromLong( (*entry_data_list)->entry_data.uint16);
    case MMDB_DATA_TYPE_UINT32:
        return PyLong_FromLong((*entry_data_list)->entry_data.uint32);
    case MMDB_DATA_TYPE_BOOLEAN:
        return PyBool_FromLong((*entry_data_list)->entry_data.boolean);
    case MMDB_DATA_TYPE_UINT64:
        return PyLong_FromUnsignedLongLong(
                   (*entry_data_list)->entry_data.uint64);
    case MMDB_DATA_TYPE_UINT128:
        return from_uint128(*entry_data_list);
    case MMDB_DATA_TYPE_INT32:
        return PyLong_FromLong((*entry_data_list)->entry_data.int32);
    default:
        PyErr_Format(MaxMindDB_error,
                     "Invalid data type arguments: %d",
                     (*entry_data_list)->entry_data.type);
        return NULL;
    }
    return NULL;
}

static PyObject *from_map(MMDB_entry_data_list_s **entry_data_list)
{
    PyObject *py_obj = PyDict_New();
    if (NULL == py_obj) {
        PyErr_NoMemory();
        return NULL;
    }

    const uint32_t map_size = (*entry_data_list)->entry_data.data_size;

    uint i;
    // entry_data_list cannot start out NULL (see from_entry_data_list). We
    // check it in the loop because it may become NULL.
    // coverity[check_after_deref]
    for (i = 0; i < map_size && entry_data_list; i++) {
        *entry_data_list = (*entry_data_list)->next;

        PyObject *key = PyUnicode_FromStringAndSize(
            (char *)(*entry_data_list)->entry_data.utf8_string,
            (*entry_data_list)->entry_data.data_size
            );

        *entry_data_list = (*entry_data_list)->next;

        PyObject *value = from_entry_data_list(entry_data_list);
        if (NULL == value) {
            Py_DECREF(key);
            Py_DECREF(py_obj);
            return NULL;
        }
        PyDict_SetItem(py_obj, key, value);
        Py_DECREF(value);
        Py_DECREF(key);
    }

    return py_obj;
}

static PyObject *from_array(MMDB_entry_data_list_s **entry_data_list)
{
    const uint32_t size = (*entry_data_list)->entry_data.data_size;

    PyObject *py_obj = PyList_New(size);
    if (NULL == py_obj) {
        PyErr_NoMemory();
        return NULL;
    }

    uint i;
    // entry_data_list cannot start out NULL (see from_entry_data_list). We
    // check it in the loop because it may become NULL.
    // coverity[check_after_deref]
    for (i = 0; i < size && entry_data_list; i++) {
        *entry_data_list = (*entry_data_list)->next;
        PyObject *value = from_entry_data_list(entry_data_list);
        if (NULL == value) {
            Py_DECREF(py_obj);
            return NULL;
        }
        // PyList_SetItem 'steals' the reference
        PyList_SetItem(py_obj, i, value);
    }
    return py_obj;
}

static PyObject *from_uint128(const MMDB_entry_data_list_s *entry_data_list)
{
    uint64_t high = 0;
    uint64_t low = 0;
#if MMDB_UINT128_IS_BYTE_ARRAY
    int i;
    for (i = 0; i < 8; i++) {
        high = (high << 8) | entry_data_list->entry_data.uint128[i];
    }

    for (i = 8; i < 16; i++) {
        low = (low << 8) | entry_data_list->entry_data.uint128[i];
    }
#else
    high = entry_data_list->entry_data.uint128 >> 64;
    low = (uint64_t)entry_data_list->entry_data.uint128;
#endif

    char *num_str = malloc(33);
    if (NULL == num_str) {
        PyErr_NoMemory();
        return NULL;
    }

    snprintf(num_str, 33, "%016" PRIX64 "%016" PRIX64, high, low);

    PyObject *py_obj = PyLong_FromString(num_str, NULL, 16);

    free(num_str);
    return py_obj;
}

static PyMethodDef Reader_methods[] = {
    { "get",      Reader_get,      METH_VARARGS,
      "Get record for IP address" },
    { "metadata", Reader_metadata, METH_NOARGS,
      "Returns metadata object for database" },
    { "close",    Reader_close,    METH_NOARGS, "Closes database"},
    { "__exit__", Reader__exit__, METH_VARARGS, "Called when exiting a with-context. Calls close"},
    { "__enter__", Reader__enter__, METH_NOARGS, "Called when entering a with-context."},
    { NULL,       NULL,            0,           NULL        }
};

static PyMemberDef Reader_members[] = {
    { "closed", T_OBJECT, offsetof(Reader_obj, closed), READONLY, NULL },
    { NULL, 0, 0, 0, NULL }
};

static PyTypeObject Reader_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_basicsize = sizeof(Reader_obj),
    .tp_dealloc = Reader_dealloc,
    .tp_doc = "Reader object",
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = Reader_methods,
    .tp_members = Reader_members,
    .tp_name = "Reader",
    .tp_init = Reader_init,
};

static PyMethodDef Metadata_methods[] = {
    { NULL, NULL, 0, NULL }
};

/* *INDENT-OFF* */
static PyMemberDef Metadata_members[] = {
    { "binary_format_major_version", T_OBJECT, offsetof(
          Metadata_obj, binary_format_major_version), READONLY, NULL },
    { "binary_format_minor_version", T_OBJECT, offsetof(
          Metadata_obj, binary_format_minor_version), READONLY, NULL },
    { "build_epoch", T_OBJECT, offsetof(Metadata_obj, build_epoch),
          READONLY, NULL },
    { "database_type", T_OBJECT, offsetof(Metadata_obj, database_type),
          READONLY, NULL },
    { "description", T_OBJECT, offsetof(Metadata_obj, description),
          READONLY, NULL },
    { "ip_version", T_OBJECT, offsetof(Metadata_obj, ip_version),
          READONLY, NULL },
    { "languages", T_OBJECT, offsetof(Metadata_obj, languages), READONLY,
          NULL },
    { "node_count", T_OBJECT, offsetof(Metadata_obj, node_count),
          READONLY, NULL },
    { "record_size", T_OBJECT, offsetof(Metadata_obj, record_size),
          READONLY, NULL },
    { NULL, 0, 0, 0, NULL }
};
/* *INDENT-ON* */

static PyTypeObject Metadata_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_basicsize = sizeof(Metadata_obj),
    .tp_dealloc = Metadata_dealloc,
    .tp_doc = "Metadata object",
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_members = Metadata_members,
    .tp_methods = Metadata_methods,
    .tp_name = "Metadata",
    .tp_init = Metadata_init
};

static PyMethodDef MaxMindDB_methods[] = {
    { NULL, NULL, 0, NULL }
};


#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef MaxMindDB_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "extension",
    .m_doc = "This is a C extension to read MaxMind DB file format",
    .m_methods = MaxMindDB_methods,
};
#endif

MOD_INIT(extension){
    PyObject *m;

#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&MaxMindDB_module);
#else
    m = Py_InitModule("extension", MaxMindDB_methods);
#endif

    if (!m) {
        RETURN_MOD_INIT(NULL);
    }

    Reader_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&Reader_Type)) {
        RETURN_MOD_INIT(NULL);
    }
    Py_INCREF(&Reader_Type);
    PyModule_AddObject(m, "Reader", (PyObject *)&Reader_Type);

    Metadata_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&Metadata_Type)) {
        RETURN_MOD_INIT(NULL);
    }
    PyModule_AddObject(m, "extension", (PyObject *)&Metadata_Type);

    PyObject* error_mod = PyImport_ImportModule("maxminddb.errors");
    if (error_mod == NULL) {
        RETURN_MOD_INIT(NULL);
    }

    MaxMindDB_error = PyObject_GetAttrString(error_mod, "InvalidDatabaseError");
    Py_DECREF(error_mod);

    if (MaxMindDB_error == NULL) {
        RETURN_MOD_INIT(NULL);
    }

    Py_INCREF(MaxMindDB_error);

    /* We primarily add it to the module for backwards compatibility */
    PyModule_AddObject(m, "InvalidDatabaseError", MaxMindDB_error);

    RETURN_MOD_INIT(m);
}
