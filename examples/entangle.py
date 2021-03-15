from __future__ import print_function

# https://www.ibm.com/developerworks/jp/cloud/library/cl-quantum-computing/index.html
import qgate
from qgate.script import *



# entangle algorithm

# allocating qubit register
qregs = new_qregs(2)
q0, q1 = qregs[0], qregs[1]


circuit = [
    H(q0),
    ctrl(q0).X(q1)
]


# measure
refs = new_references(2)
circuit += [
    measure(refs[0], qregs[0]),
    measure(refs[1], qregs[1])
]

sim = qgate.simulator.py()
sim.run(circuit)

obs = sim.obs(refs)
print('observation\n'
      '(c0, c1) = ({}, {})'.format(obs(refs[0]), obs(refs[1])))


sim.terminate()
