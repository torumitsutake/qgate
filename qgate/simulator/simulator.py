import qgate.model.model as model
import numpy as np
import math
import random
            

def _op_key(op_tuple) :
    return op_tuple[0].idx


# creg arrays and their values.
class CregDict :
    def __init__(self, creg_arrays) :
        self.creg_dict = dict()
        for creg_array in creg_arrays :
            values = np.zeros([len(creg_array)])
            self.creg_dict[creg_array] = values

    def get_arrays(self) :
        return self.creg_dict.keys()
    
    def set_value(self, creg, value) :
        values = self.creg_dict[creg.creg_array]
        values[creg.idx] = value
        
    def get_value(self, creg) :
        values = self.creg_dict[creg.creg_array]
        return values[creg.idx]

    def get_values(self, creg_array) :
        return self.creg_dict[creg_array]

    def get_array_as_integer(self, creg_array) :
        values = self.creg_dict[creg_array]
        ivalue = 0
        for idx, value in enumerate(values) :
            if value == 1 :
                ivalue |= 1 << idx
        return ivalue


class Simulator :
    def __init__(self, runtime) :
        self.runtime = runtime
        self.qubits = runtime.Qubits()

    def set_program(self, program) :
        self.program = program
        
    def get_qubits(self) :
        return self.qubits
    
    def get_creg_dict(self) :
        return self.creg_dict

    def prepare(self) :
        ops = []

        circuits = self.program.get_circuits()
        for circuit_idx, circuit in enumerate(circuits) :
            ops += [(op, circuit_idx) for op in circuit.ops]

        # FIXME: basic operator ordering
        ops = sorted(ops, key = _op_key)
        self.ops = ops
        
        for circuit_idx, circuit in enumerate(circuits) :
            self.qubits.allocate_qubit_states(circuit_idx, circuit.qregs)
        
        self.creg_dict = CregDict(self.program.creg_arrays)

        self.bit_values = [ -1 for _ in range(len(self.program.qregs)) ]
        
        self.step_iter = iter(self.ops)

    def run_step(self) :
        try :
            op_circ = next(self.step_iter)
            op = op_circ[0]
            qstates = self.qubits[op_circ[1]]
            self._apply_op(op, qstates)
            return True
        except StopIteration :
            return False

    def run(self) :
        while self.run_step() :
            pass

    def terminate(self) :
        # release resources.
        self.qubit_groups = None
        self.creg_array_dict = None
        self.program = None
        self.ops = None
        
    def _apply_op(self, op, qstates) :
        if isinstance(op, model.Clause) :
            self._apply_clause(op, qstates)
        elif isinstance(op, model.IfClause) :
            self._apply_if_clause(op, qstates)
        elif isinstance(op, model.Measure) :
            self._measure(op, qstates)
        elif isinstance(op, model.UnaryGate) :
            self._apply_unary_gate(op, qstates)
        elif isinstance(op, model.ControlGate) :
            self._apply_control_gate(op, qstates)
        elif isinstance(op, model.Barrier) :
            pass  # Since this simulator runs step-wise, able to ignore barrier.
        elif isinstance(op, model.Reset) :
            self._apply_reset(op, qstates)
        else :
            assert False, "Unknown operator."

    def _apply_if_clause(self, op, qstates) :
        if self.creg_dict.get_array_as_integer(op.creg_array) == op.val :
            self._apply_op(op.clause, qstates)

    def _apply_clause(self, op, qstates) :
        for clause_op in op.ops :
            self._apply_op(clause_op, qstates)
    
    def _measure(self, op, qstates) :
        for in0, creg in zip(op.in0, op.cregs) :
            rand_num = random.random()
            creg_value = self.runtime.measure(rand_num, qstates, in0)
            self.creg_dict.set_value(creg, creg_value)
            self.bit_values[in0.id] = creg_value

    def _apply_reset(self, op, qstates) :
        for qreg in op.qregset :
            bitval = self.bit_values[qreg.id]
            if bitval == -1 :
                raise RuntimeError('Qubit is not measured.')
            if bitval == 1 :
                self.runtime.apply_reset(qstates, qreg)

            self.bit_values[qreg.id] = -1
                    
    def _apply_unary_gate(self, op, qstates) :
        for in0 in op.in0 :
            self.runtime.apply_unary_gate(op.get_matrix(), qstates, in0)

    def _apply_control_gate(self, op, qstates) :
        for in0, in1 in zip(op.in0, op.in1) :
            self.runtime.apply_control_gate(op.get_matrix(), qstates, in0, in1)
