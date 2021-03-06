/* -*- c++ -*- */

#include "pyglue.h"
#include "CUDAQubitStates.h"
#include "CUDAQubitProcessor.h"
#include "CUDAQubitsStatesGetter.h"
#include "CUDAGlobals.h"

namespace qcuda = qgate_cuda;

namespace {

void module_initialize(PyObject *module) {
    try {
        qcuda::cudaDevices.probe();
    }
    catch (...) {
        qcuda::cudaDevices.finalize();
        throw;
    }
}

PyObject *module_finalize(PyObject *module, PyObject *) {
    qcuda::cudaDevices.synchronize();
    qcuda::cudaMemoryStore.finalize();
    qcuda::cudaDevices.finalize();
    Py_INCREF(Py_None);
    return Py_None;
}

extern "C"
PyObject *devices_initialize(PyObject *module, PyObject *args) {
    PyObject *objDeviceIds;
    int maxPo2idxPerChunk;
    qgate::QstateSize memoryStoreSize;
    if (!PyArg_ParseTuple(args, "OiL", &objDeviceIds, &maxPo2idxPerChunk, &memoryStoreSize))
        return NULL;
    
    qgate::IdList deviceNos = toIdList(objDeviceIds);
    qcuda::cudaDevices.create(deviceNos);

    /* FIXME: move to CUDADevices. */
    qgate::QstateSize minDeviceMemorySize =  qcuda::cudaDevices.getMinDeviceMemorySize();
    if (maxPo2idxPerChunk == -1) {
        maxPo2idxPerChunk = 40;
        qgate::QstateSize chunkSize;
        do {
            --maxPo2idxPerChunk;
            chunkSize = qgate::Qone << maxPo2idxPerChunk;
        } while (minDeviceMemorySize / chunkSize < 3);
    }
    /* memoryStoreSize may be -1, allowing to use actual device free size. */
    qcuda::cudaMemoryStore.initialize(qcuda::cudaDevices, maxPo2idxPerChunk, memoryStoreSize);
    
    Py_INCREF(Py_None);
    return Py_None;
}

extern "C"
PyObject *devices_clear(PyObject *module, PyObject *args) {
    qcuda::cudaDevices.synchronize();
    qcuda::cudaMemoryStore.finalize();
    qcuda::cudaDevices.clear();
    
    Py_INCREF(Py_None);
    return Py_None;
}

extern "C"
PyObject *qubit_states_new(PyObject *module, PyObject *args) {
    PyObject *dtype;
    if (!PyArg_ParseTuple(args, "O", &dtype))
        return NULL;
    
    qgate::QubitStates *qstates = NULL;
    if (isFloat64(dtype))
        qstates = new qcuda::CUDAQubitStates<double>();
    else if (isFloat32(dtype))
        qstates = new qcuda::CUDAQubitStates<float>();
    else
        abort_("unexpected dtype.");
    
    PyObject *obj = PyArrayScalar_New(UInt64);
    PyArrayScalar_ASSIGN(obj, UInt64, (npy_uint64)qstates);
    return obj;
}


extern "C"
PyObject *qubit_processor_new(PyObject *module, PyObject *args) {
    PyObject *dtype;
    if (!PyArg_ParseTuple(args, "O", &dtype))
        return NULL;

    qgate::QubitProcessor *qproc = NULL;
    if (isFloat64(dtype))
        qproc = new qcuda::CUDAQubitProcessor<double>(qcuda::cudaDevices);
    else if (isFloat32(dtype))
        qproc = new qcuda::CUDAQubitProcessor<float>(qcuda::cudaDevices);
    else
        abort_("unexpected dtype.");
    
    PyObject *obj = PyArrayScalar_New(UInt64);
    PyArrayScalar_ASSIGN(obj, UInt64, (npy_uint64)qproc);
    return obj;
}

extern "C"
PyObject *qubits_states_getter_new(PyObject *module, PyObject *args) {
    PyObject *dtype;
    if (!PyArg_ParseTuple(args, "O", &dtype))
        return NULL;

    qgate::QubitsStatesGetter *qproc = NULL;
    if (isFloat64(dtype))
        qproc = new qcuda::CUDAQubitsStatesGetter<double>();
    else if (isFloat32(dtype))
        qproc = new qcuda::CUDAQubitsStatesGetter<float>();
    else
        abort_("unexpected dtype.");
    
    PyObject *obj = PyArrayScalar_New(UInt64);
    PyArrayScalar_ASSIGN(obj, UInt64, (npy_uint64)qproc);
    return obj;
}

static
PyMethodDef cudaext_methods[] = {
    {"module_finalize", module_finalize, METH_VARARGS},
    {"devices_initialize", devices_initialize, METH_VARARGS},
    {"devices_clear", devices_clear, METH_VARARGS},
    {"qubit_states_new", qubit_states_new, METH_VARARGS},
    {"qubit_processor_new", qubit_processor_new, METH_VARARGS},
    {"qubits_states_getter_new", qubits_states_getter_new, METH_VARARGS},
    {NULL},
};

}



#define modname "cudaext"
#define INIT_MODULE INITFUNCNAME(cudaext)

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        modname,
        NULL, 0,
        cudaext_methods,
        NULL, NULL, NULL, NULL
};

extern "C"
PyMODINIT_FUNC INIT_MODULE(void) {
    PyObject *module = PyModule_Create(&moduledef);
    if (module == NULL)
        return NULL;
    import_array();
    try {
        module_initialize(module);
    }
    catch (const std::runtime_error &e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        Py_DECREF(module);
        return NULL;
    }
    return module;
}

#else

PyMODINIT_FUNC INIT_MODULE(void) {
    PyObject *module = Py_InitModule(modname, cudaext_methods);
    if (module == NULL)
        return;
    import_array();
    try {
        module_initialize(module);
    }
    catch (const std::runtime_error &e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
    }
}

#endif
