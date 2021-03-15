from __future__ import print_function

# https://www.ibm.com/developerworks/jp/cloud/library/cl-quantum-computing/index.html
import qgate
from qgate.script import *

def Tdag(qred):
    return [
        [T(qred) for i in range(7)]
    ]
# allocating qubit register
qregs = new_qregs(5)
q0, q1, q2, q3 = qregs[0], qregs[1],qregs[2], qregs[3]

# building a quantum circuit.

#circuit = [
#    [H(qreg) for qreg in qregs]
#]
#f(x) = 4^x(mod15)
#4 =  0100
#15 = 1111
circuit = [
    H(q0),H(q1),
    ctrl(q1).X(q2),
    X(q3),ctrl(q1).X(q3)
    ]
circuit += [
    H(q0),
    [T(q1) for i in range(7)],
    ctrl(q0).X(q1),
    T(q1),
    ctrl(q0).X(q1),
    H(q1),
    [T(q0) for i in range(7)],
    ctrl(q0).X(q1),
    ctrl(q1).X(q0),
    ctrl(q0).X(q1)
]

# measure
refs = new_references(4)
circuit += [
    measure(refs[0], qregs[1]),
    measure(refs[1], qregs[0])
]

count0 = 0
count1 = 0
count2 = 0
count3 = 0

for i in range(100):
    sim = qgate.simulator.py()
    sim.run(circuit)
    obs = sim.obs(refs)
    print('observation\n'
          '(c0, c1) = ({}, {})'.format(obs(refs[0]), obs(refs[1])))
    print(obs)
    c0 = obs(refs[0])
    c1 = obs(refs[1])
    if c0 == 0 and c1 == 0:
        count0 += 1
    if c0 == 1 and c1 == 0:
        count1 += 1
    if c0 == 0 and c1 == 1:
        count2 += 1
    if c0 == 1 and c1 == 1:
        count3 += 1

print("count0",count0)
print("count1",count1)
print("count2",count2)
print("count3",count3)

#print('\ndump state vector:')
#qgate.dump(sim.qubits)

sim.terminate()
