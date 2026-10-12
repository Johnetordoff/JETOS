#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    PyObject_HEAD
    Py_ssize_t size;
    unsigned char *data;
} NativeBufferObject;

static PyObject *
NativeBuffer_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    NativeBufferObject *self;
    (void)args;
    (void)kwargs;
    self = (NativeBufferObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->size = 0;
        self->data = NULL;
    }
    return (PyObject *)self;
}

static int
NativeBuffer_init(NativeBufferObject *self, PyObject *args, PyObject *kwargs)
{
    Py_ssize_t size;
    static char *keywords[] = {"size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "n:NativeBuffer", keywords, &size)) {
        return -1;
    }
    if (size < 0) {
        PyErr_SetString(PyExc_ValueError, "size must be non-negative");
        return -1;
    }
    PyMem_Free(self->data);
    self->data = NULL;
    self->size = size;
    if (size > 0) {
        self->data = PyMem_Calloc((size_t)size, sizeof(unsigned char));
        if (self->data == NULL) {
            self->size = 0;
            PyErr_NoMemory();
            return -1;
        }
    }
    return 0;
}

static void
NativeBuffer_dealloc(NativeBufferObject *self)
{
    PyMem_Free(self->data);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static Py_ssize_t
NativeBuffer_length(PyObject *object)
{
    return ((NativeBufferObject *)object)->size;
}

static PyObject *
NativeBuffer_fill(NativeBufferObject *self, PyObject *value_object)
{
    long value = PyLong_AsLong(value_object);
    if (value == -1 && PyErr_Occurred()) {
        return NULL;
    }
    if (value < 0 || value > 255) {
        PyErr_SetString(PyExc_ValueError, "fill value must be between 0 and 255");
        return NULL;
    }
    if (self->size > 0) {
        memset(self->data, (unsigned char)value, (size_t)self->size);
    }
    Py_RETURN_NONE;
}

static PyObject *
NativeBuffer_copy_from(NativeBufferObject *self, PyObject *object)
{
    Py_buffer view;
    if (PyObject_GetBuffer(object, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    if (view.len != self->size) {
        PyBuffer_Release(&view);
        PyErr_Format(
            PyExc_ValueError,
            "source length %zd does not match buffer size %zd",
            view.len,
            self->size
        );
        return NULL;
    }
    if (self->size > 0) {
        memcpy(self->data, view.buf, (size_t)self->size);
    }
    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

static PyObject *
NativeBuffer_to_bytes(NativeBufferObject *self, PyObject *Py_UNUSED(ignored))
{
    return PyBytes_FromStringAndSize((const char *)self->data, self->size);
}

static PyObject *
NativeBuffer_checksum64(NativeBufferObject *self, PyObject *Py_UNUSED(ignored))
{
    uint64_t hash = UINT64_C(1469598103934665603);
    Py_ssize_t index;
    for (index = 0; index < self->size; index++) {
        hash ^= (uint64_t)self->data[index];
        hash *= UINT64_C(1099511628211);
    }
    return PyLong_FromUnsignedLongLong(hash);
}

static PyObject *
NativeBuffer_get_size(NativeBufferObject *self, void *closure)
{
    (void)closure;
    return PyLong_FromSsize_t(self->size);
}

static PyMethodDef NativeBuffer_methods[] = {
    {"fill", (PyCFunction)NativeBuffer_fill, METH_O, "Fill the buffer in pure C."},
    {"copy_from", (PyCFunction)NativeBuffer_copy_from, METH_O, "Copy bytes into native storage."},
    {"to_bytes", (PyCFunction)NativeBuffer_to_bytes, METH_NOARGS, "Return an immutable bytes copy."},
    {"checksum64", (PyCFunction)NativeBuffer_checksum64, METH_NOARGS, "Return a 64-bit FNV-1a checksum."},
    {NULL, NULL, 0, NULL}
};

static PyGetSetDef NativeBuffer_getset[] = {
    {"size", (getter)NativeBuffer_get_size, NULL, "buffer size", NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PySequenceMethods NativeBuffer_sequence = {
    .sq_length = NativeBuffer_length,
};

static PyTypeObject NativeBufferType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "jetos._jetos_native.NativeBuffer",
    .tp_basicsize = sizeof(NativeBufferObject),
    .tp_itemsize = 0,
    .tp_dealloc = (destructor)NativeBuffer_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "C-backed byte buffer exposed as a Python object.",
    .tp_methods = NativeBuffer_methods,
    .tp_getset = NativeBuffer_getset,
    .tp_as_sequence = &NativeBuffer_sequence,
    .tp_init = (initproc)NativeBuffer_init,
    .tp_new = NativeBuffer_new,
};

static PyObject *
jetos_xor_bytes(PyObject *module, PyObject *args)
{
    Py_buffer input;
    unsigned int key;
    PyObject *output;
    char *target;
    Py_ssize_t index;
    (void)module;

    if (!PyArg_ParseTuple(args, "y*I:xor_bytes", &input, &key)) {
        return NULL;
    }
    if (key > 255U) {
        PyBuffer_Release(&input);
        PyErr_SetString(PyExc_ValueError, "key must be between 0 and 255");
        return NULL;
    }
    output = PyBytes_FromStringAndSize(NULL, input.len);
    if (output == NULL) {
        PyBuffer_Release(&input);
        return NULL;
    }
    target = PyBytes_AS_STRING(output);
    for (index = 0; index < input.len; index++) {
        target[index] = (char)(((const unsigned char *)input.buf)[index] ^ (unsigned char)key);
    }
    PyBuffer_Release(&input);
    return output;
}

static PyMethodDef module_methods[] = {
    {"xor_bytes", jetos_xor_bytes, METH_VARARGS, "XOR a bytes-like object in pure C."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module_definition = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_jetos_native",
    .m_doc = "JETOS target-native C acceleration and native-object spine.",
    .m_size = -1,
    .m_methods = module_methods,
};

PyMODINIT_FUNC
PyInit__jetos_native(void)
{
    PyObject *module;
    if (PyType_Ready(&NativeBufferType) < 0) {
        return NULL;
    }
    module = PyModule_Create(&module_definition);
    if (module == NULL) {
        return NULL;
    }
    Py_INCREF(&NativeBufferType);
    if (PyModule_AddObject(module, "NativeBuffer", (PyObject *)&NativeBufferType) < 0) {
        Py_DECREF(&NativeBufferType);
        Py_DECREF(module);
        return NULL;
    }
    if (PyModule_AddStringConstant(module, "backend", "c-extension") < 0) {
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
