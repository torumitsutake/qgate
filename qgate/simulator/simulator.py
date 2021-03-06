from .qubits import Qubits
from .value_store import ValueStore
from .qubits_handler import QubitsHandler
import qgate.model as model
from qgate.model.gatelist import GateListIterator
from .model_executor import ModelExecutor
from .runtime_operator import Observer
from .observation import Observation, ObservationList
import numpy as np
import math


class Simulator :
    def __init__(self, defpkg, **prefs) :
        dtype = prefs.get('dtype', np.float64)
        self.prefs = dict()
        self.set_preference(**prefs)
        states_getter = defpkg.create_qubits_states_getter(dtype)
        self._qubits = Qubits(states_getter, dtype) # FIXME: remove
        self._value_store = ValueStore()
        self._qhandler = QubitsHandler(defpkg.create_qubit_states, self._qubits)
        self.executor = ModelExecutor(self._qhandler, self._value_store)
        self.reset()

    @property
    def qubits(self) :
        return self._qubits

    @property
    def values(self) :
        return self._value_store

    def set_preference(self, **prefs) :
        self.prefs = dict(prefs.items())

    def reset(self) :
        # release all internal objects
        self._qhandler.reset()
        self._value_store.reset()
        self.preprocessor = model.Preprocessor(**self.prefs)

    def terminate(self) :
        # release resources.
        self._qubits = None
        self._qhandler = None
        self._value_store = None
        self.circuits = None
        self.ops = None

    def obs(self, reflist) :
        if isinstance(reflist, model.Reference) :
            reflist = [reflist]
        value = self._value_store.get_packed_value(reflist)
        mask = self._value_store.get_mask(reflist)
        return Observation(reflist, value, mask)

    def run(self, circuit) :
        if not isinstance(circuit, model.GateList) :
            ops = circuit
            circuit = model.GateList()
            circuit.set(ops)
            
        preprocessed = self.preprocessor.preprocess(circuit)
        
        # model.dump(preprocessed)

        self._value_store.sync_refs(self.preprocessor.get_refset())

        self.op_iter = GateListIterator(preprocessed.ops)
        while True :
            op = self.op_iter.next()
            if op is None :
                break
            if isinstance(op, model.IfClause) :
                if self._evaluate_if(op) :
                    self.op_iter.prepend(op.clause)
            else :
                self.executor.enqueue(op)

        self.executor.flush()
        self._qubits.update_external_layout()
        for qstates in self.qubits.qstates_list :
            qstates.processor.synchronize()

    def sample(self, circuit, ref_array, n_samples = 1024) :
        if not isinstance(circuit, model.GateList) :
            ops = circuit
            circuit = model.GateList()
            circuit.set(ops)

        obs = np.empty([n_samples], dtype = np.int64)
        
        self.reset()
        preprocessed = self.preprocessor.preprocess(circuit)

        for loop in range(n_samples) :
            self.reset()
            self._value_store.sync_refs(self.preprocessor.get_refset())

            self.op_iter = GateListIterator(preprocessed.ops)
            while True :
                op = self.op_iter.next()
                if op is None :
                    break
                if isinstance(op, model.IfClause) :
                    if self._evaluate_if(op) :
                        self.op_iter.prepend(op.clause)
                else :
                    self.executor.enqueue(op)

            self.executor.flush()

            packed_value = self._value_store.get_packed_value(ref_array)
            obs[loop] = packed_value

        for qstates in self.qubits.qstates_list :
            qstates.processor.synchronize()
        mask = self._value_store.get_mask(ref_array)
        return ObservationList(ref_array, obs, mask)

    def _evaluate_if(self, op) :
        # wait for referred value obtained.
        for obj in self._value_store.get(op.refs) :
            if isinstance(obj, model.Measure) :
                self.executor.wait_op(obj)  # wait for Measure op dispatched in model executor.
        for obj in self._value_store.get(op.refs) :
            if isinstance(obj, Observer) and not obj.observed :
                self.executor.wait_observable(obj) # wait for value is set.

        if callable(op.cond) :
            values = self._value_store.get(op.refs)
            return op.cond(*values)
        else :
            packed_value = self._value_store.get_packed_value(op.refs)
            return packed_value == op.cond
