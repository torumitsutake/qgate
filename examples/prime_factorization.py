from __future__ import print_function

# https://www.ibm.com/developerworks/jp/cloud/library/cl-quantum-computing/index.html
import qgate
from qgate.script import *

# Glover's algorithm

# allocating qubit register
qregs = new_qregs(4)
q0, q1, q2, q3 = qregs[0], qregs[1],qregs[2], qregs[3]

# building a quantum circuit.
circuit = [
    [H(qreg) for qreg in qregs],
    H(q1),
    ctrl(q0).X(q1),
    H(q1),
    [H(qreg) for qreg in qregs],
    [X(qreg) for qreg in qregs],
    H(q1),
    ctrl(q0).X(q1),
    H(q1),
    [X(qreg) for qreg in qregs],
    [H(qreg) for qreg in qregs]
]
circuit = [
    H(q0),H(q1),
    ctrl(q1).X(q2),
    X(q3),ctrl(q1).X(q3),
    H(q0),T(q1),Z(q1),
    ctrl(q0).X(q1),
    T(q1),
    ctrl(q0).X(q1),
    H(q1),T(q0),Z(q0),
    ctrl(q0).X(q1),
    ctrl(q1).X(q0),
    ctrl(q0).X(q1)
]


# measure
refs = new_references(4)
circuit += [
    measure(refs[0], qregs[0]),
    measure(refs[1], qregs[1])
]

sim = qgate.simulator.py()
sim.run(circuit)

obs = sim.obs(refs)
print('observation\n'
      '(c0, c1) = ({}, {})'.format(obs(refs[0]), obs(refs[1])))
print(obs)

print('\ndump state vector:')
qgate.dump(sim.qubits)

sim.terminate()
