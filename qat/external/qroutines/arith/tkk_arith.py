# -*- coding: utf-8 -*-
"""Ripple carry adder example based on [TaTK10] Takahashi, Yasuhiro ; Tani,
Seiichiro ; Kunihiro, Noboru: Quantum addition circuits and unbounded fan-out.
In: Quantum Information & Computation Bd. 10 (2010), Nr. 9 & 10, S. 872–890.
— Citation Key: DBLP:journals/qic/TakahashiTK10

"""

import itertools
import logging

from qat.lang.AQASM.gates import CCNOT, CNOT, X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

LOGGER = logging.getLogger(__name__)

def _adder(qrout, a, b, c_reg, little_endian=False):
    a_new = a + c_reg
    rlen = len(a)
    # if not little_endian:
    #     a_new.reverse()
    #     b.reverse()

    # print("*1*")
    i = None
    for i in range(1, rlen):
        qrout.apply(CNOT, a[i], b[i])
    if i is not None:
        qrout.apply(CNOT, a[i], c_reg)

    # print("*2*")
    for i in range(rlen - 1, 1, -1):
        qrout.apply(CNOT, a[i - 1], a[i])

    # print("*3*")
    for i in range(0, rlen):
        qrout.apply(CCNOT, a[i], b[i], a_new[i + 1])

    # print("*4*")
    for i in range(rlen - 1, 0, -1):
        qrout.apply(CNOT, a[i], b[i])
        qrout.apply(CCNOT, a[i - 1], b[i - 1], a[i])

    # print("*5*")
    for i in range(1, rlen - 1):
        qrout.apply(CNOT, a[i], a[i + 1])

    # print("*6*")
    for i in range(0, rlen):
        qrout.apply(CNOT, a[i], b[i])


@build_gate("MADD", [int, int, bool, bool])
def adder(a_len: int, b_len: int, overflow_qubit = False, little_endian=False) -> QRoutine:
    # assuming same length for now
    assert a_len == b_len
    rlen = a_len
    qrout = QRoutine()
    a = qrout.new_wires(rlen)
    b = qrout.new_wires(rlen)
    c_reg = qrout.new_wires(1)
    if not overflow_qubit:
        qrout.set_ancillae(c_reg)

    _adder(qrout, a, b, c_reg, little_endian)
    return qrout

@build_gate("MSUB", [int, int, bool, bool])
def subtractor(a_len: int, b_len: int, overflow_qubit = False, little_endian=False) -> QRoutine:
    assert a_len == b_len
    rlen = a_len
    qrout = QRoutine()
    a = qrout.new_wires(rlen)
    b = qrout.new_wires(rlen)
    c_reg = qrout.new_wires(1)
    if not overflow_qubit:
        qrout.set_ancillae(c_reg)

    for qb in itertools.chain(a):
        qrout.apply(X, qb)
    _adder(qrout, a, b, c_reg, little_endian)

    for qb in itertools.chain(a, b):
        qrout.apply(X, qb)
    return qrout
