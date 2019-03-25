/**
 * markupsafe._speedups
 * ~~~~~~~~~~~~~~~~~~~~
 *
 * C implementation of escaping for better performance. Used instead of
 * the native Python implementation when compiled.
 *
 * :copyright: © 2010 by the Pallets team.
 * :license: BSD, see LICENSE for more details.
 */
#include <Python.h>

#if PY_MAJOR_VERSION < 3
#define ESCAPED_CHARS_TABLE_SIZE 63
#define UNICHR(x) (PyUnicode_AS_UNICODE((PyUnicodeObject*)PyUnicode_DecodeASCII(x, strlen(x), NULL)));

static Py_ssize_t escaped_chars_delta_len[ESCAPED_CHARS_TABLE_SIZE];
static Py_UNICODE *escaped_chars_repl[ESCAPED_CHARS_TABLE_SIZE];
#endif

static PyObject* markup;

static int
init_constants(void)
{
	PyObject *module;

#if PY_MAJOR_VERSION < 3
	/* mapping of characters to replace */
	escaped_chars_repl['"'] = UNICHR("&#34;");
	escaped_chars_repl['\''] = UNICHR("&#39;");
	escaped_chars_repl['&'] = UNICHR("&amp;");
	escaped_chars_repl['<'] = UNICHR("&lt;");
	escaped_chars_repl['>'] = UNICHR("&gt;");

	/* lengths of those characters when replaced - 1 */
	memset(escaped_chars_delta_len, 0, sizeof (escaped_chars_delta_len));
	escaped_chars_delta_len['"'] = escaped_chars_delta_len['\''] = \
		escaped_chars_delta_len['&'] = 4;
	escaped_chars_delta_len['<'] = escaped_chars_delta_len['>'] = 3;
#endif

	/* import markup type so that we can mark the return value */
	module = PyImport_ImportModule("markupsafe");
	if (!module)
		return 0;
	markup = PyObject_GetAttrString(module, "Markup");
	Py_DECREF(module);

	return 1;
}

#if PY_MAJOR_VERSION < 3
static PyObject*
escape_unicode(PyUnicodeObject *in)
{
	PyUnicodeObject *out;
	Py_UNICODE *inp = PyUnicode_AS_UNICODE(in);
	const Py_UNICODE *inp_end = PyUnicode_AS_UNICODE(in) + PyUnicode_GET_SIZE(in);
	Py_UNICODE *next_escp;
	Py_UNICODE *outp;
	Py_ssize_t delta=0, erepl=0, delta_len=0;

	/* First we need to figure out how long the escaped string will be */
	while (*(inp) || inp < inp_end) {
		if (*inp < ESCAPED_CHARS_TABLE_SIZE) {
			delta += escaped_chars_delta_len[*inp];
			erepl += !!escaped_chars_delta_len[*inp];
		}
		++inp;
	}

	/* Do we need to escape anything at all? */
	if (!erepl) {
		Py_INCREF(in);
		return (PyObject*)in;
	}

	out = (PyUnicodeObject*)PyUnicode_FromUnicode(NULL, PyUnicode_GET_SIZE(in) + delta);
	if (!out)
		return NULL;

	outp = PyUnicode_AS_UNICODE(out);
	inp = PyUnicode_AS_UNICODE(in);
	while (erepl-- > 0) {
		/* look for the next substitution */
		next_escp = inp;
		while (next_escp < inp_end) {
			if (*next_escp < ESCAPED_CHARS_TABLE_SIZE &&
			    (delta_len = escaped_chars_delta_len[*next_escp])) {
				++delta_len;
				break;
			}
			++next_escp;
		}

		if (next_escp > inp) {
			/* copy unescaped chars between inp and next_escp */
			Py_UNICODE_COPY(outp, inp, next_escp-inp);
			outp += next_escp - inp;
		}

		/* escape 'next_escp' */
		Py_UNICODE_COPY(outp, escaped_chars_repl[*next_escp], delta_len);
		outp += delta_len;

		inp = next_escp + 1;
	}
	if (inp < inp_end)
		Py_UNICODE_COPY(outp, inp, PyUnicode_GET_SIZE(in) - (inp - PyUnicode_AS_UNICODE(in)));

	return (PyObject*)out;
}
#else /* PY_MAJOR_VERSION < 3 */

#define GET_DELTA(inp, inp_end, delta) \
	while (inp < inp_end) {	 \
		switch (*inp++) {	   \
		case '"':			   \
		case '\'':			  \
		case '&':			   \
			delta += 4;		 \
			break;			  \
		case '<':			   \
		case '>':			   \
			delta += 3;		 \
			break;			  \
		}					   \
	}

#define DO_ESCAPE(inp, inp_end, outp) \
	{  \
		Py_ssize_t ncopy = 0;  \
		while (inp < inp_end) {  \
			switch (*inp) {  \
			case '"':  \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&';  \
				*outp++ = '#';  \
				*outp++ = '3';  \
				*outp++ = '4';  \
				*outp++ = ';';  \
				break;  \
			case '\'':  \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&';  \
				*outp++ = '#';  \
				*outp++ = '3';  \
				*outp++ = '9';  \
				*outp++ = ';';  \
				break;  \
			case '&':  \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&';  \
				*outp++ = 'a';  \
				*outp++ = 'm';  \
				*outp++ = 'p';  \
				*outp++ = ';';  \
				break;  \
			case '<':  \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&';  \
				*outp++ = 'l';  \
				*outp++ = 't';  \
				*outp++ = ';';  \
				break;  \
			case '>':  \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&';  \
				*outp++ = 'g';  \
				*outp++ = 't';  \
				*outp++ = ';';  \
				break;  \
			default:  \
				ncopy++; \
			}  \
            inp++; \
		}  \
		memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
	}

static PyObject*
escape_unicode_kind1(PyUnicodeObject *in)
{
	Py_UCS1 *inp = PyUnicode_1BYTE_DATA(in);
	Py_UCS1 *inp_end = inp + PyUnicode_GET_LENGTH(in);
	Py_UCS1 *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		Py_INCREF(in);
		return (PyObject*)in;
	}

	out = PyUnicode_New(PyUnicode_GET_LENGTH(in) + delta,
						PyUnicode_IS_ASCII(in) ? 127 : 255);
	if (!out)
		return NULL;

	inp = PyUnicode_1BYTE_DATA(in);
	outp = PyUnicode_1BYTE_DATA(out);
	DO_ESCAPE(inp, inp_end, outp);
	return out;
}

static PyObject*
escape_unicode_kind2(PyUnicodeObject *in)
{
	Py_UCS2 *inp = PyUnicode_2BYTE_DATA(in);
	Py_UCS2 *inp_end = inp + PyUnicode_GET_LENGTH(in);
	Py_UCS2 *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		Py_INCREF(in);
		return (PyObject*)in;
	}

	out = PyUnicode_New(PyUnicode_GET_LENGTH(in) + delta, 65535);
	if (!out)
		return NULL;

	inp = PyUnicode_2BYTE_DATA(in);
	outp = PyUnicode_2BYTE_DATA(out);
	DO_ESCAPE(inp, inp_end, outp);
	return out;
}


static PyObject*
escape_unicode_kind4(PyUnicodeObject *in)
{
	Py_UCS4 *inp = PyUnicode_4BYTE_DATA(in);
	Py_UCS4 *inp_end = inp + PyUnicode_GET_LENGTH(in);
	Py_UCS4 *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		Py_INCREF(in);
		return (PyObject*)in;
	}

	out = PyUnicode_New(PyUnicode_GET_LENGTH(in) + delta, 1114111);
	if (!out)
		return NULL;

	inp = PyUnicode_4BYTE_DATA(in);
	outp = PyUnicode_4BYTE_DATA(out);
	DO_ESCAPE(inp, inp_end, outp);
	return out;
}

static PyObject*
escape_unicode(PyUnicodeObject *in)
{
	if (PyUnicode_READY(in))
		return NULL;

	switch (PyUnicode_KIND(in)) {
	case PyUnicode_1BYTE_KIND:
		return escape_unicode_kind1(in);
	case PyUnicode_2BYTE_KIND:
		return escape_unicode_kind2(in);
	case PyUnicode_4BYTE_KIND:
		return escape_unicode_kind4(in);
	}
	assert(0);  /* shouldn't happen */
	return NULL;
}
#endif /* PY_MAJOR_VERSION < 3 */

static PyObject*
escape(PyObject *self, PyObject *text)
{
	static PyObject *id_html;
	PyObject *s = NULL, *rv = NULL, *html;

	if (id_html == NULL) {
#if PY_MAJOR_VERSION < 3
		id_html = PyString_InternFromString("__html__");
#else
		id_html = PyUnicode_InternFromString("__html__");
#endif
		if (id_html == NULL) {
			return NULL;
		}
	}

	/* we don't have to escape integers, bools or floats */
	if (PyLong_CheckExact(text) ||
#if PY_MAJOR_VERSION < 3
	    PyInt_CheckExact(text) ||
#endif
	    PyFloat_CheckExact(text) || PyBool_Check(text) ||
	    text == Py_None)
		return PyObject_CallFunctionObjArgs(markup, text, NULL);

	/* if the object has an __html__ method that performs the escaping */
	html = PyObject_GetAttr(text ,id_html);
	if (html) {
		s = PyObject_CallObject(html, NULL);
		Py_DECREF(html);
		/* Convert to Markup object */
		rv = PyObject_CallFunctionObjArgs(markup, (PyObject*)s, NULL);
		Py_DECREF(s);
		return rv;
	}

	/* otherwise make the object unicode if it isn't, then escape */
	PyErr_Clear();
	if (!PyUnicode_Check(text)) {
#if PY_MAJOR_VERSION < 3
		PyObject *unicode = PyObject_Unicode(text);
#else
		PyObject *unicode = PyObject_Str(text);
#endif
		if (!unicode)
			return NULL;
		s = escape_unicode((PyUnicodeObject*)unicode);
		Py_DECREF(unicode);
	}
	else
		s = escape_unicode((PyUnicodeObject*)text);

	/* convert the unicode string into a markup object. */
	rv = PyObject_CallFunctionObjArgs(markup, (PyObject*)s, NULL);
	Py_DECREF(s);
	return rv;
}


static PyObject*
escape_silent(PyObject *self, PyObject *text)
{
	if (text != Py_None)
		return escape(self, text);
	return PyObject_CallFunctionObjArgs(markup, NULL);
}


static PyObject*
soft_unicode(PyObject *self, PyObject *s)
{
	if (!PyUnicode_Check(s))
#if PY_MAJOR_VERSION < 3
		return PyObject_Unicode(s);
#else
		return PyObject_Str(s);
#endif
	Py_INCREF(s);
	return s;
}


static PyMethodDef module_methods[] = {
	{"escape", (PyCFunction)escape, METH_O,
	 "escape(s) -> markup\n\n"
	 "Convert the characters &, <, >, ', and \" in string s to HTML-safe\n"
	 "sequences.  Use this if you need to display text that might contain\n"
	 "such characters in HTML.  Marks return value as markup string."},
	{"escape_silent", (PyCFunction)escape_silent, METH_O,
	 "escape_silent(s) -> markup\n\n"
	 "Like escape but converts None to an empty string."},
	{"soft_unicode", (PyCFunction)soft_unicode, METH_O,
	 "soft_unicode(object) -> string\n\n"
         "Make a string unicode if it isn't already.  That way a markup\n"
         "string is not converted back to unicode."},
	{NULL, NULL, 0, NULL}		/* Sentinel */
};


#if PY_MAJOR_VERSION < 3

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_speedups(void)
{
	if (!init_constants())
		return;

	Py_InitModule3("markupsafe._speedups", module_methods, "");
}

#else /* Python 3.x module initialization */

static struct PyModuleDef module_definition = {
        PyModuleDef_HEAD_INIT,
	"markupsafe._speedups",
	NULL,
	-1,
	module_methods,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC
PyInit__speedups(void)
{
	if (!init_constants())
		return NULL;

	return PyModule_Create(&module_definition);
}

#endif
