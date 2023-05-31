import logging

import numpy as np
from qat.lang.AQASM.gates import CNOT, RY, X
from qat.lang.AQASM.routines import QRoutine
from qat.lang.AQASM.misc import build_gate

logger = logging.getLogger(__name__)


@build_gate("_BARTSCHI_I", [float])
def _igate(angle: float) -> QRoutine:
    qf = QRoutine()
    wires = qf.new_wires(2)
    # n-2 -> 0, n-1 -> 1
    qf.apply(CNOT, wires[0], wires[1])
    qf.apply(RY(angle).ctrl(), wires[1], wires[0])
    qf.apply(CNOT, wires[0], wires[1])
    return qf


@build_gate("_BARTSCHI_II", [float])
def _iigate(angle: float) -> QRoutine:
    qf = QRoutine()
    wires = qf.new_wires(3)
    # n-l-1 -> 0, n-l -> 1, n - 1 ->2
    qf.apply(CNOT, wires[0], wires[2])
    qf.apply(RY(angle).ctrl(2), wires[2], wires[1], wires[0])
    qf.apply(CNOT, wires[0], wires[2])
    return qf


def _scs(n: int, k: int) -> QRoutine:
    qf = QRoutine()
    wires = qf.new_wires(n)
    angle = 2 * np.arccos(1 / np.sqrt(n))
    # (i)
    # n-2 -> 0, n-1 -> 1
    qf.apply(_igate(angle), wires[n - 2], wires[n - 1])
    # qfi.apply(CNOT, wires[n - 2], wires[n - 1])
    # qfi.apply(RY(angle).ctrl(), wires[n - 1], wires[n - 2])
    # qfi.apply(CNOT, wires[n - 2], wires[n - 1])
    # (ii)_l
    for l in range(2, k + 1):
        angle = 2 * np.arccos(np.sqrt(l / n))
        # n-l-1 -> 0, n-l -> 1, n - 1 ->2
        qf.apply(_iigate(angle), n - l - 1, n - l, n - 1)
        # qf.apply(CNOT, wires[n - l - 1], wires[n - 1])
        # qf.apply(RY(angle).ctrl(2), wires[n - 1], wires[n - l], wires[n - l - 1])
        # qf.apply(CNOT, wires[n - l - 1], wires[n - 1])
    return qf


@build_gate("DICKE", [int, int])
def generate(n: int, k: int) -> QRoutine:
    qf = QRoutine()
    wires = qf.new_wires(n)
    if k <= 0 or n < k:
        return qf
    if k == n:
        for qb in wires:
            qf.apply(X, qb)
        return qf

    localk = k if k <= n / 2 else n - k
    for i in range(n - 1, n - localk - 1, -1):
        qf.apply(X, wires[i])

    for i in range(n, localk, -1):
        qf.apply(_scs(i, localk), wires[:i])
    for i in range(localk, 1, -1):
        qf.apply(_scs(i, i - 1), wires[:i])

    if localk != k:
        for qb in wires:
            qf.apply(X, qb)
    return qf
