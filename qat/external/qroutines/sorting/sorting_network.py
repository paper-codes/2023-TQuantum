"""See http://staff.ustc.edu.cn/~csli/graduate/algorithms/book6/chap28.htm and
https://fileadmin.cs.lth.se/cs/Personal/Rolf_Karlsson/lect10.pdf for reference.

The original work is in Chapter 27.3,4,5 of T. H. Cormen, C. E.
Leiserson, R. L. Rivest, and C. Stein, Introduction to algorithms,
second edition. The MIT Press and McGraw-Hill Book Company, 2001.
"""
import logging
from typing import Any, Dict

import numpy as np
from qat.lang.AQASM.gates import SWAP, CNOT, X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

_LOGGER = logging.getLogger(__name__)


def _build_gate_common(net_data: Dict[str, Any]) -> QRoutine:
    a_len: int = net_data["n_lines"]
    comp_len: int = net_data["n_comps"]
    routine = QRoutine()
    a_wires = routine.new_wires(a_len)
    comp_wires = routine.new_wires(comp_len)

    for swap_pattern in net_data["swaps_pattern"]:
        a_qb = a_wires[swap_pattern[1]]
        b_qb = a_wires[swap_pattern[2]]
        ctrl_qb = comp_wires[swap_pattern[0]]
        # Compare qubits 1 and 2 and put the output in pattern 0
        # routine.apply(two_bit_comparator(), a_qb, b_qb, ctrl_qb)
        # 
        # New, equivalent version, with one less CCNOT and one more CNOT
        routine.apply(X, b_qb)
        routine.apply(CNOT, b_qb, ctrl_qb)
        routine.apply(X, b_qb)
        #
        routine.apply(SWAP.ctrl(), ctrl_qb, a_qb, b_qb)
    return routine


@build_gate("BITONIC_SORTER", [dict])
def build_gate_bitonic_sorter(net_data: Dict[str, Any]) -> QRoutine:
    return _build_gate_common(net_data)


def get_pattern_bitonic_sorter(n) -> Dict[str, Any]:
    """Given how it's built, n should be a power of 2 and, if not, it returns
    the combination rounding up to the top power of 2. If the original n is not
    a power of 2, you may want to adapt the circuit avoiding the use of the
    last bits.

    Returns a dictionary containing the:
    1. n_lines, the number of lines required; it is the rounding up of n to the
    closest power of 2

    2. n_comps, the number of fair coin flips required to obtain the full
    permutation

    3. the swaps_pattern, i.e. a list of tuples containing:
    - an integer signalling which comparator output bit to use
    - the first line involved in the swap
    - the second line involved in the swap
    """
    net_data = {}
    steps = int(np.ceil(np.log2(n)))
    net_data["n_lines"] = 2**steps
    net_data["swaps_pattern"] = []
    initial_swaps = int(net_data["n_lines"] / 2)

    _get_pattern_bitonic_sorter(
        0, initial_swaps, int(net_data["n_lines"] / 2), 0, net_data
    )
    net_data["n_comps"] = len(net_data["swaps_pattern"])
    return net_data


def _get_pattern_bitonic_sorter(start, end, swap_step, comp_q_idx, net_data):
    _LOGGER.debug("Start: %d, end: %d, swap_step: %d", start, end, swap_step)
    if swap_step == 0 or start >= end:
        _LOGGER.debug("Base case recursion")
        return comp_q_idx

    for_iter = 0
    for i in range(start, end):
        for_iter += 1
        _LOGGER.info("cswap(%d, %d, %d)", comp_q_idx, i, i + swap_step)
        net_data["swaps_pattern"].append((comp_q_idx, i, i + swap_step))
        comp_q_idx += 1

    for_iter_next = min(for_iter, int(swap_step / 2))
    _LOGGER.debug(
        "Before rec1, start: %d, end: %d, swap_step: %d, for_iter_next %d",
        start,
        end,
        swap_step,
        for_iter_next,
    )
    comp_q_idx = _get_pattern_bitonic_sorter(
        start, start + for_iter_next, int(swap_step / 2), comp_q_idx, net_data
    )
    _LOGGER.debug(
        "Before rec, start: %d, end: %d, swap_step: %d, for_iter_next %d",
        start,
        end,
        swap_step,
        for_iter_next,
    )
    comp_q_idx = _get_pattern_bitonic_sorter(
        start + swap_step,
        start + swap_step + for_iter_next,
        int(swap_step / 2),
        comp_q_idx,
        net_data,
    )
    return comp_q_idx


@build_gate("MERGER", [dict])
def build_gate_merger(net_data: dict):
    return _build_gate_common(net_data)


def get_pattern_merger(n):
    net_data = {}
    comp_q_idx = _get_pattern_merger_support(n, net_data, 0)

    net_data["n_comps"] = len(net_data["swaps_pattern"])
    return net_data


def _get_pattern_merger_support(n, net_data, comp_q_idx, start_shift=0):
    steps = int(np.ceil(np.log2(n)))
    net_data["n_lines"] = 2**steps
    net_data["swaps_pattern"] = net_data.get("swaps_pattern", [])
    initial_swaps = int(net_data["n_lines"] / 2)

    for i in range(initial_swaps):
        net_data["swaps_pattern"].append(
            (comp_q_idx, i + start_shift, net_data["n_lines"] - i - 1 + start_shift)
        )
        comp_q_idx += 1

    # the second half of the circuit is identical to the bitonic sorter
    start = start_shift
    swap_step = int(initial_swaps / 2)
    comp_q_idx = _get_pattern_bitonic_sorter(
        start, start + swap_step, swap_step, comp_q_idx, net_data
    )
    comp_q_idx = _get_pattern_bitonic_sorter(
        start + swap_step * 2, start + swap_step * 3, swap_step, comp_q_idx, net_data
    )
    return comp_q_idx


@build_gate("SORTER", [dict])
def build_gate_sorter(net_data):
    return _build_gate_common(net_data)


def get_pattern_sorter(n):
    net_data = {}
    lis = []

    _get_pattern_sorter_support(0, n, lis)

    comp_q_idx = 0
    # Note that, since the last pattern to be analyzed is the greatest one, we
    # obtain as side effect the right number of 'n_lines'
    for start, end in reversed(lis):
        n = len(range(start, end))
        comp_q_idx = _get_pattern_merger_support(n, net_data, comp_q_idx, start)
        net_data["n_comps"] = len(net_data["swaps_pattern"])
    return net_data


def _get_pattern_sorter_support(start, end, acc, depth=0):
    # rec_string = '>' * depth
    # print(f"{rec_string}recursion start")
    # print(f"{rec_string}merger [{start}-{end})")
    pattern = (start, end)
    acc.append(pattern)
    if start + 2 >= end:
        # input(f"{rec_string}base case")
        return

    mid = int((start + end) / 2)
    # print(f"{rec_string}before recursion 1")
    _get_pattern_sorter_support(start, mid, acc, depth + 1)
    # print(f"{rec_string}before recursion 2")
    _get_pattern_sorter_support(mid, end, acc, depth + 1)
    return
