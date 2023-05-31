import logging

import numpy as np
from qat.lang.AQASM.gates import X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

LOGGER = logging.getLogger(__name__)


def get_required_ancillae(nrows: int, ncols: int):
    """Get the number of additional (swap_ancilla, add_ancilla) qubits required
    for the RREF.

    :param nrows: Rows of matrix
    :param ncols: Cols of matrix
    :returns: (swap_ancilla, add_ancilla)
    """
    nsquare = min(nrows, ncols)
    add_ancilla_n = nsquare * (nsquare - 1)
    # Add ancilla is necessary an even number
    swap_ancilla_n = int(add_ancilla_n / 2)
    return swap_ancilla_n, add_ancilla_n


def build_u_matrix_from_sample(sample, nsquare):
    """Build the matrix of transformations applied to obtain the RREF. I.e.,
    if.

    original matrix was A and its RREF is B, we have U * B = A.

    This function will return the U matrix by analyzing the intermediate
    measurements on the ancilla (swap and add) qubits produced by the RREF
    gate.
    """
    if len(sample.intermediate_measurements) != 2:
        return
    # this creates a bitlist
    inter_meas_aout, inter_meas_bout = [
        i.cbits for i in sample.intermediate_measurements
    ]
    return build_u_matrix_from_bitlists(inter_meas_aout, inter_meas_bout, nsquare)


def build_u_matrix_from_bitstrings(swaps: str, adds: str, nsquare):
    return build_u_matrix_from_bitlists(
        [int(i) for i in swaps], [int(i) for i in adds], nsquare
    )


def build_u_matrix_from_bitlists(swaps: list, adds: list, nsquare):
    """Build the matrix of transformations applied to obtain the RREF. I.e.,
    if.

    original matrix was A and its RREF is B, we have U * B = A.

    This function will return the U matrix by analyzing the ancilla qubits
    produced by the RREF gate.
    """
    swap_idx = 0
    add_idx = 0
    u = np.eye(nsquare, dtype=np.uint8)
    for i in range(nsquare):
        for j in range(i + 1, nsquare):
            if swaps[swap_idx]:
                u[i,] += u[j,]
            swap_idx += 1
        for j in range(nsquare):
            if j == i:
                continue
            if adds[add_idx]:
                u[j,] += u[i,]
            add_idx += 1
    u = u % 2
    return u


@build_gate("RREF_OPS", [int, int])
def gate_same_ops_for_vector(nrows: int, ncols: int):
    """Apply the same operations applied to obtain the matrix RREF to a vector.
    The.

    idea is that if originally we had A*x = y, now we'll have A_rref * x =
    y_rref.

    :param nrows: The number of rows of the original matrix A
    :param ncols: The number of cols of the original matrix A
    :returns: A qroutine taking as input (in this order)
       - vector_qreg
       - swap_qreg
       - add_qreg
    """
    qfun = QRoutine()
    vec_wires = qfun.new_wires(nrows)
    swap_ancilla_n, add_ancilla_n = get_required_ancillae(nrows, ncols)
    swap_wires = qfun.new_wires(swap_ancilla_n)
    add_wires = qfun.new_wires(add_ancilla_n)

    idx = 0
    for i in range(nrows):
        for j in range(i + 1, nrows):
            qfun.apply(X.ctrl(2), swap_wires[idx], vec_wires[j], vec_wires[i])
            idx += 1

    idx = 0
    for i in range(nrows):
        for j in range(nrows):
            if i != j:
                qfun.apply(X.ctrl(2), add_wires[idx], vec_wires[i], vec_wires[j])
                idx += 1

    return qfun


@build_gate("RREF", [int, int])
def get_rref(nrows, ncols):
    """Apply RREF to a matrix A.

    :param nrows: The number of rows of the original matrix A
    :param ncols: The number of cols of the original matrix A
    The gate takes as input, in this order:
    - The matrix (nrows x ncols), represented as qreg
    - The swap ancillae
    - The add ancillae

    The number of swap and add ancillae required can be obtained through the
    get_ancillae function.
    """
    qrout = QRoutine()

    qregs_rows = []
    for _ in range(nrows):
        # qregs_rows.append(qregs_init.ini)
        qreg = qrout.new_wires(ncols)
        qregs_rows.append(qreg)

    nsquare = min(nrows, ncols)
    swap_ancilla_n, add_ancilla_n = get_required_ancillae(nrows, ncols)
    swap_ancillae = qrout.new_wires(swap_ancilla_n)
    add_ancillae = qrout.new_wires(add_ancilla_n)
    add_ancilla_idx = 0
    swap_ancilla_idx = 0

    for i in range(nsquare):
        if i != nrows - 1:
            # we don't apply swap gates for the last row
            swap_gate = get_row_swap(nrows, ncols, i)
            # swap_ancilla = qrout.new_wires(swap_ancillan)
            swap_len = len(range(i + 1, nrows))
            # print(f"Row {i}")
            # print(f"qregs {[j for j in qregs_rows[i]]}")
            qrout.apply(
                swap_gate,
                *qregs_rows,
                swap_ancillae[swap_ancilla_idx : swap_ancilla_idx + swap_len],
            )
            swap_ancilla_idx += swap_len

        add_len = nrows - 1
        bgate = get_row_addition(nrows, ncols, i)
        qrout.apply(
            bgate,
            *qregs_rows,
            add_ancillae[add_ancilla_idx : add_ancilla_idx + add_len],
        )
        add_ancilla_idx += add_len

    return qrout


@build_gate("ROWSWAP", [int, int, int])
def get_row_swap(nrows, ncols, row_src_idx: int):
    """In reality just add to the source row the first row with non-zero
    element. F.e., suppose:

    - row_src_idx = 0
    - rows = [[0, 1, 0], [1, 0, 0], [0, 1, 1]]

    If rows[row_src_idx][row_src_idx] == 0: # True
    - then we search for the first row (row_oth_idx) having a non-zero element
      in the same row_src_idx # 1 in this case
    - and then do rows[row_src_idx] += rows[row_oth_idx]

    Note that the element of rows are qregister, each one representing a row.
    Each qregister should have the same length, otw the result is undefined.
    """
    LOGGER.debug(f"nrows {nrows}, ncols {ncols}")
    qfun = QRoutine()

    # This will contain the source row
    row_wires = []
    for _ in range(nrows):
        row_wires.append(qfun.new_wires(ncols))

    # the pivot is on the diagonal
    col_src_idx = row_src_idx
    LOGGER.debug(f"row_src_idx {row_src_idx}")
    row_src = row_wires[row_src_idx]
    LOGGER.debug(f"row src {row_src}")
    # LOGGER.debug(f"row src idxs {[q.index for q in row_src]}")
    LOGGER.debug(f"X src {row_src[row_src_idx]} ")
    qfun.apply(X, row_src[col_src_idx])
    for row_oth_idx in range(row_src_idx + 1, nrows):
        # All the possible rows after the source row
        LOGGER.debug(f"row_oth_idx {row_oth_idx}")
        row_oth = row_wires[row_oth_idx]
        LOGGER.debug(f"row oth {row_oth}")
        # LOGGER.debug(f"row oth idxs {[q.index for q in row_oth]}")

        # Ancilla telling if the column must be swapped; since it's not reset
        # to 0, I can't add it to the ancillae list
        anc = qfun.new_wires(1)
        # qfun.set_ancillae(anc)
        # LOGGER.debug(f"ancillae {qfun.ancillae}")
        LOGGER.debug(f"current ancilla {anc}")
        # LOGGER.debug(f"current ancilla idx {anc[0].index}")
        # CNOT where ctrl must be 0
        # row_src[col_idx] can be 1 in two cases:
        # - It has been set to 1 in the previous round following a swap
        # - It was already 1 to start with
        LOGGER.debug(f"CNOT {row_src[col_src_idx]} -> {anc} ")
        qfun.apply(X.ctrl(), row_src[col_src_idx], anc)

        # sum if ancilla is set, but only the col_idxs after the given one. The
        # idea is that all previous idx are already at 0 bcz of previous row
        # operations.
        for col_idx in range(col_src_idx, ncols):
            LOGGER.debug(f"CCNOT {anc}, {row_oth[col_idx]} -> {row_src[col_idx]} ")
            qfun.apply(X.ctrl(2), anc, row_oth[col_idx], row_src[col_idx])

    LOGGER.debug(f"X src {row_src[col_src_idx]} ")
    qfun.apply(X, row_src[col_src_idx])
    return qfun


@build_gate("ROWADD", [int, int, int])
def get_row_addition(nrows, ncols, row_src_idx: int):
    qfun = QRoutine()
    # nrows, ncols = len(matrix), len(matrix[0])
    LOGGER.debug(f"nrows {nrows}, ncols {ncols}")

    # This will contain the source row
    # row_src = qfun.new_wires(row_length)
    row_wires = []
    for _ in range(nrows):
        row_wires.append(qfun.new_wires(ncols))

    col_src_idx = row_src_idx
    LOGGER.debug(f"row_src_idx {row_src_idx}")
    row_src = row_wires[row_src_idx]
    LOGGER.debug(f"row src {row_src}")
    # LOGGER.debug(f"row src idxs {[q.index for q in row_src]}")
    # WIP diff, range
    for row_oth_idx in range(nrows):
        if row_oth_idx == row_src_idx:
            continue
        # All the possible rows after the source row
        LOGGER.debug(f"row_oth_idx {row_oth_idx}")
        row_oth = row_wires[row_oth_idx]
        LOGGER.debug(f"row oth {row_oth}")
        # LOGGER.debug(f"row oth idxs {[q.index for q in row_oth]}")
        # Ancilla telling if the column must be swapped
        anc = qfun.new_wires(1)
        # qfun.set_ancillae(anc)
        # LOGGER.debug(f"ancillae {qfun.ancillae}")
        LOGGER.debug(f"current ancilla {anc}")
        # LOGGER.debug(f"current ancilla idx {anc[0].index}")
        # CNOT where ctrl must be 0
        # row_src[col_idx] can be 1 in two cases:
        # - It has been set to 1 in the previous round following a swap
        # - It was already 1 to start with
        LOGGER.debug(f"CNOT {row_src[col_src_idx]} -> {anc} ")
        qfun.apply(X.ctrl(), row_oth[col_src_idx], anc)

        # sum if ancilla is set, but only the col_idxs after the given one. The
        # idea is that all previous idx are already at 0 bcz of previous row
        # operations.
        # WIP, diff, CCNOT src and tgt
        for col_idx in range(col_src_idx, ncols):
            LOGGER.debug(f"CCNOT {anc}, {row_oth[col_idx]} -> {row_src[col_idx]} ")
            qfun.apply(X.ctrl(2), anc, row_src[col_idx], row_oth[col_idx])

    LOGGER.debug("----")
    return qfun
