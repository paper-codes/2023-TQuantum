"""This gauss-jordan procedure is specifically tailored for ISD."""
import logging
from functools import partial

from qat.lang.AQASM.gates import CCNOT, CNOT, X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

LOGGER = logging.getLogger(__name__)
# Just a fake swap for pictorial representation of deleted gates
# FAKE = X


def get_required_ancillae(r: int) -> tuple[int, int]:
    """Get the number of additional (swap_ancilla, add_ancilla) qubits required
    for the RREF.

    :param nrows: Rows of matrix
    :returns: (swap_ancilla, add_ancilla)
    """
    # Add ancilla is necessary an even number, so there is no actual rounding here
    swap_ancilla_n = (r * (r - 1)) // 2
    # Add ancilla not necessary anymore
    # add_ancilla_n = r * (r - 1)
    return swap_ancilla_n, 0


@build_gate("GJISD", [int, int, bool, int])
def get_rref(r, n, skip_rightmost, norig) -> QRoutine:
    """Apply RREF to a matrix H.

    :param r: The number of rows of the original matrix H
    :param n: The number of cols of the original matrix H
    :param skip_rightmost: Skip the operations on the rightmost r*k submatrix (used in Prange)
    :param norig is the number of columns of original matrix. In theory, param n can be composed by the original matrix plus the syndrome columns.
    The gate takes as input, in this order:
    - The matrix (r * n), represented as qreg
    - The swap ancillae

    The number of swap and add ancillae required can be obtained through the
    get_ancillae function.

    WARN: if you pass the syndrome(s) as well as columns of the matrix, you
    should put them at the end of the original matrix (i.e., after column n-1)
    """
    qrout = QRoutine()
    if norig < 0:
        norig = n

    qregs_rows = []
    for _ in range(r):
        qreg = qrout.new_wires(n)
        qregs_rows.append(qreg)

    swap_ancilla_n, _ = get_required_ancillae(r)
    swap_ancillae = qrout.new_wires(swap_ancilla_n)
    swap_ancilla_idx = 0

    if skip_rightmost:
        # in Prange we skip the rightmost r X k columns of original matrix H
        skip_cols = set(range(r, norig))
    else:
        skip_cols = set()

    qrout.apply(X, qregs_rows[0][0])
    for x in range(r):
        _skip_cols = skip_cols.copy()
        rowswap = partial(get_row_swap, r, n, x, _skip_cols)
        rowadd = partial(get_row_addition, r, n, x, _skip_cols)
        # we don't check the pivot for the last row, we'll check at later
        # stages if it's equal to 1
        if x != r - 1:
            # phase 1, look for a valid pivot in rows below
            for i in range(x + 1, r):
                pivot_last = i == r - 1
                qrout.apply(
                    rowswap(pivot_last),
                    qregs_rows[x],
                    qregs_rows[i],
                    swap_ancillae[swap_ancilla_idx],
                )
                swap_ancilla_idx += 1
            # improvement 3, X anticipated
            if x != r - 2:
                qrout.apply(X, qregs_rows[x + 1][x + 1])  #

        if x != r - 1:
            qrout.apply(X, qregs_rows[x][x])

        # phase 2, put 0 in pivot column for each row below and above pivot one
        for i in range(r):
            # obv, we skip the row under analysis
            if i == x:
                continue
            qrout.apply(
                rowadd(),
                qregs_rows[i],
                qregs_rows[x],
            )
        # impr. 1
        skip_cols.add(x)

    return qrout


@build_gate("ROWSWAP", [int, int, int, set, bool])
def get_row_swap(r: int, n: int, pivot_idx: int, skip_cols: set, pivot_last: bool):
    """WARN: the pivot element is checked against state 1 (improvement 4)
    r, n: ISD params
    pivot_idx: index of pivot under analysis (in the matrix, it has position M_{pivot_idx, pivot_idx})
    skip_cols: indexes of columns to skip. Used f.e. in improvement 1
    pivot_last: if true, pivot element swap will be performed after the other r elements of the matrix, but before the last ks (improvement 5)
    """
    qrout = QRoutine()
    pivot_row = qrout.new_wires(n)
    other_row = qrout.new_wires(n)
    anc = qrout.new_wires(1)
    qrout.apply(CNOT, pivot_row[pivot_idx], anc)

    # we do the first rs, then (if pivot last as per impr. 5) we do pivot, then last ks
    for c in range(r):
        if c not in skip_cols:
            if c == pivot_idx and pivot_last:
                continue
            qrout.apply(CCNOT, anc, other_row[c], pivot_row[c])
    # impr. 5
    if pivot_last:
        qrout.apply(CCNOT, anc, other_row[pivot_idx], pivot_row[pivot_idx])
    for c in range(r, n):
        if c not in skip_cols:
            qrout.apply(CCNOT, anc, other_row[c], pivot_row[c])
    return qrout


@build_gate("ROWADD", [int, int, int, set])
def get_row_addition(r: int, n: int, pivot_idx: int, skip_cols: set):
    """
    r, n: ISD params
    pivot_idx: index of pivot under analysis (in the matrix, it has position M_{pivot_idx, pivot_idx})
    skip_cols: indexes of columns to skip
    pivot_last: if true, pivot element swap will be performed after the other r elements of the matrix, but before the last ks (improvement 6)
    """

    qrout = QRoutine()
    other_row = qrout.new_wires(n)
    pivot_row = qrout.new_wires(n)
    # anc = qrout.new_wires(1)
    # qrout.apply(CNOT, other_row[pivot_idx], anc)
    for c in range(r):
        # pivot_last. 6
        if c == pivot_idx:
            continue
        elif c not in skip_cols:
            qrout.apply(CCNOT, other_row[pivot_idx], pivot_row[c], other_row[c])
    # pivot_last. 6 + 2
    # qrout.apply(CNOT, anc, other_row[pivot_idx])
    for c in range(r, n):
        if c not in skip_cols:
            qrout.apply(CCNOT, other_row[pivot_idx], pivot_row[c], other_row[c])
    return qrout
