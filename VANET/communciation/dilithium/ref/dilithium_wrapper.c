#include <Python.h>
#include <stdlib.h>
#include "params.h"
#include "sign.h"
#include "api.h"

static PyObject* dilithium_keygen(PyObject* self, PyObject* args) {
    uint8_t pk[CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[CRYPTO_SECRETKEYBYTES];
    
    // Updated function call with correct parameters
    pqcrystals_dilithium2_ref_keypair(pk, sk);
    
    return Py_BuildValue("(y#)(y#)", 
        pk, CRYPTO_PUBLICKEYBYTES,
        sk, CRYPTO_SECRETKEYBYTES
    );
}

static PyObject* dilithium_sign(PyObject* self, PyObject* args) {
    const uint8_t* sk;
    Py_ssize_t sk_len;
    const uint8_t* msg;
    Py_ssize_t msg_len;
    const uint8_t* ctx = NULL;
    Py_ssize_t ctx_len = 0;

    if (!PyArg_ParseTuple(args, "y#y#|y#", &sk, &sk_len, &msg, &msg_len, &ctx, &ctx_len)) return NULL;
    if (sk_len != CRYPTO_SECRETKEYBYTES) return NULL;

    uint8_t* sm = (uint8_t*)malloc(msg_len + CRYPTO_BYTES);
    size_t sm_len;
    
    // Updated function call with correct signature
    int result = pqcrystals_dilithium2_ref(sm, &sm_len, msg, msg_len, ctx, ctx_len, sk);
    if (result != 0) {
        free(sm);
        PyErr_SetString(PyExc_RuntimeError, "Failed to create signature");
        return NULL;
    }

    PyObject* py_result = Py_BuildValue("y#", sm, (Py_ssize_t)sm_len);
    free(sm);
    return py_result;
}

static PyMethodDef DilithiumMethods[] = {
    {"keygen", dilithium_keygen, METH_NOARGS, "Generate Dilithium2 key pair"},
    {"sign", dilithium_sign, METH_VARARGS, "Create Dilithium2 signature"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef dilithium_module = {
    PyModuleDef_HEAD_INIT,
    "dilithium",
    "Python wrapper for Dilithium2",
    -1,
    DilithiumMethods
};

PyMODINIT_FUNC PyInit_dilithium(void) {
    return PyModule_Create(&dilithium_module);
}
