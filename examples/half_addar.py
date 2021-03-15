from __future__ import print_function

# https://www.ibm.com/developerworks/jp/cloud/library/cl-quantum-computing/index.html
import qgate
from qgate.script import *



# Glover's algorithm

# allocating qubit register
qregs = new_qregs(3)
q0, q1, q2 = qregs[0], qregs[1], qregs[2]

#input
circuit = [I(qreg) for qreg in qregs]
circuit += [
    X(q0)
]

circuit += [
ctrl(q0,q1).X(q2),
ctrl(q0).X(q1)
]


# measure
refs = new_references(3)
circuit += [
    measure(refs[0], qregs[0]),
    measure(refs[1], qregs[1]),
    measure(refs[2], qregs[2])
]

sim = qgate.simulator.py()
sim.run(circuit)

obs = sim.obs(refs)
print('observation\n'
      '(c0, c1, c2) = ({}, {}, {})'.format(obs(refs[0]), obs(refs[1]), obs(refs[2])))


sim.terminate()
