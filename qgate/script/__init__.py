from __future__ import absolute_import

from .script import new_qreg, new_qregs, new_reference, new_references, new_circuit, measure, barrier, reset, clause, if_
# gate factory
from .script import a, h, s, t, x, y, z, rx, ry, rz, u1, u2, u3, controlled, cntr

#from . import qelib1
from qgate.model.processor import process