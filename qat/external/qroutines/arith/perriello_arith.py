from qat.lang.AQASM.gates import CCNOT, CNOT, X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine


@build_gate("CONST1_ADDER", [int])
def add_one(n: int, overflow_qubit = False, little_endian = False) -> QRoutine:
    """Add one to a qreg.
    If  overflow_qubit is True, """
    pass
    # qrout = QRoutine()
    # qrout.apply(X, 0)
    # for i in range(n-1):
    #     qrout.apply(CNOT, i, i+1)


@build_gate("2BIT_ADDER", [])
def two_bit_adder() -> QRoutine:
    """The out qubit should be initialized to 0.

    Given two 1-qubit registers a and b, it returns 1 on the output
    qubit if a > b.
    """
    qrout = QRoutine()
    a = qrout.new_wires(1)
    b = qrout.new_wires(1)
    c = qrout.new_wires(1)

    qrout.apply(CNOT, a, b)
    qrout.apply(X, b)
    qrout.apply(CCNOT, a, b, c)
    qrout.apply(X, b)

    return qrout

@build_gate("2BIT_COMP", [])
def two_bit_comparator() -> QRoutine:
    """The out qubit should be initialized to 0.

    Given two 1-qubit registers a and b, it returns 1 on the output
    qubit if a > b.
    """
    qrout = QRoutine()
    a = qrout.new_wires(1)
    b = qrout.new_wires(1)
    c = qrout.new_wires(1)

    # b must be negated since we want to have a + (-b)
    qrout.apply(X, b)
    qrout.apply(CCNOT, a, b, c)
    qrout.apply(X, b)

    return qrout
