# -*- coding: utf-8 -*-
"""Ripple adder example based on Cuccaro et al., quant-ph/0410184."""

import itertools
import logging

from qat.lang.AQASM.gates import CCNOT, CNOT, X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

# from .fake import fake

LOGGER = logging.getLogger(__name__)


def _common_init(a_l, b_l, overflow_qbit, little_endian):
    """We are performing |a>|b> -> |a>|a+b> (or smthg similar, depending on the
    calling function). If len(b) > 1, then it allocates a new qubit for the carry-in, as per cuccaro scheme

    :param a_l, b_l: length of registers a and b, resp.
    :param overflow_qbit: if True, we need another additional ancilla containing the outcome of the (possible) overflow of the addition
    :little_endian: if a and b are expected to be in BIG ENDIAN or LITTLE ENDIAN format"""
    bits = min(a_l, b_l)
    # b_l contains the result
    b_is_bigger = b_l > bits

    qfun = QRoutine()
    a = qfun.new_wires(a_l)
    b = qfun.new_wires(b_l)
    if not little_endian:
        a.reverse()
        b.reverse()
    # Just for graphical purposes
    # for i, aq in enumerate(a):
    #     qfun.apply(fake(f"a{i}"), aq)
    # for i, bq in enumerate(b):
    #     qfun.apply(fake(f"b{i}"), bq)
    LOGGER.debug("a %s", a)
    LOGGER.debug("b %s", b)
    # When Cuccaro adder is used, we need an additional cin, that will be restored to 0 after the addition.
    cin = qfun.new_wires(1)
    qfun.set_ancillae(cin)
    LOGGER.debug("cin %s", cin)

    if overflow_qbit:
        cout = qfun.new_wires(1)
        # qfun.apply(fake("cout"), cout[0])
        LOGGER.debug("cout %s", cout)
    else:
        cout = None

    return qfun, a, b, cin, cout, bits, b_is_bigger


def _common(qfun, a, b, cout, bits, overflow_qbit):
    a_l = len(a)
    b_l = len(b)
    if b_l == 1:
        qfun.apply(CNOT, a[0], b[0])
        if overflow_qbit:
            qfun.apply(X, b[0])
            qfun.apply(CCNOT, a[0], b[0], cout[0])
            qfun.apply(X, b[0])
            if a_l > bits:
                qfun.apply(CNOT, a[1], cout[0])
        return None, None, None

    sub = 0 if (overflow_qbit or b_l > a_l) else 1
    LOGGER.debug("sub is %d", sub)
    end = bits - 1
    ends = end - sub
    mrange = range(0, ends)
    LOGGER.debug("mrange %s", mrange)
    return mrange, end, ends


def _maj_chain(qfun, a, b, cin, mrange):
    LOGGER.debug("MAJ %d, %d, %d", cin[0], b[0], a[0])
    qfun.apply(_majority(f"cin, b{0}, a{0}"), cin[0], b[0], a[0])
    for j in mrange:
        LOGGER.debug("j is %d", j)
        LOGGER.debug("MAJ %d, %d, %d", a[j], b[j + 1], a[j + 1])
        qfun.apply(_majority(f"a{j}, b{j+1}, a{j+1}"), a[j], b[j + 1], a[j + 1])


def _maj_chain_dag(qfun, a, b, cin, mrange):
    for j in reversed(mrange):
        LOGGER.debug("j is %d", j)
        LOGGER.debug("MAJD %d, %d, %d", a[j], b[j + 1], a[j + 1])
        qfun.apply(_majority(f"a{j}, b{j+1}, a{j+1}").dag(), a[j], b[j + 1], a[j + 1])
    LOGGER.debug("MAJD %d, %d, %d", cin[0], b[0], a[0])
    qfun.apply(_majority(f"cin, b{0}, a{0}").dag(), cin[0], b[0], a[0])


def _middle_logic(qfun, a, b, cout, end, ends, overflow_qbit, b_is_bigger):
    a_l = len(a)
    b_l = len(b)
    # MIDDLE LOGIC ###
    if not b_is_bigger:
        outbit = cout[0] if overflow_qbit else b[end]
        LOGGER.debug("b is not bigger")
        LOGGER.debug("CNOT %d, %d", a[end], outbit)

        qfun.apply(CNOT, a[ends], outbit)
        if not overflow_qbit and a_l == b_l:
            # Simple modulo 2^b_l operation, as in Cuccaro's paper
            LOGGER.debug("CNOT %d, %d", a[ends], outbit)
            qfun.apply(CNOT, a[end], outbit)
        elif a_l > b_l:
            LOGGER.debug("CNOT %d, %d", a[ends + 1], outbit)
            qfun.apply(CNOT, a[ends + 1], outbit)
    else:
        # b_l > bits -> b extends past end
        # Additional logic to take care of different size regs, not
        # present in Cuccaro
        outbit = cout[0] if overflow_qbit else b[-1]
        LOGGER.debug("b is bigger")
        nslice = b[end + 2 : b_l : 1]
        LOGGER.debug("nslice %s", nslice)
        chain = itertools.chain(nslice, cout) if overflow_qbit else nslice
        LOGGER.debug("CNOT %d, %d", a[end], b[end + 1])
        qfun.apply(CNOT, a[ends], b[end + 1])
        prv_tgt_1 = a[ends]
        prv_tgt = b[end + 1]
        for cur_tgt in chain:
            LOGGER.debug("X %s", prv_tgt)
            qfun.apply(X, prv_tgt)
            LOGGER.debug("CCNOT %s %s %s", prv_tgt_1, prv_tgt, cur_tgt)
            qfun.apply(CCNOT, prv_tgt_1, prv_tgt, cur_tgt)
            LOGGER.debug("X %s", prv_tgt)
            qfun.apply(X, prv_tgt)
            prv_tgt = cur_tgt


def _unmaj_chain(qfun, a, b, cin, mrange):
    # UNM CHAIN ###
    for j in reversed(mrange):
        LOGGER.debug("j is %d", j)
        LOGGER.debug("UNM %d, %d, %d", a[j], b[j + 1], a[j + 1])
        qfun.apply(_unmajority(f"a{j}, b{j+1}, a{j+1}"), a[j], b[j + 1], a[j + 1])
    LOGGER.debug("UNM %d, %d, %d", cin[0], b[0], a[0])
    qfun.apply(_unmajority(f"cin, b{0}, a{0}"), cin[0], b[0], a[0])


@build_gate("MCOMP", [int, int, bool])
def comparator(a_l: int, b_l: int, little_endian=False) -> QRoutine:
    overflow_qbit = True
    qfun, a, b, cin, cout, bits, b_is_bigger = _common_init(
        a_l, b_l, overflow_qbit, little_endian
    )
    for qb in a:
        qfun.apply(X, qb)

    mrange, end, ends = _common(qfun, a, b, cout, bits, overflow_qbit)
    if mrange is not None:
        _maj_chain(qfun, a, b, cin, mrange)
        _middle_logic(qfun, a, b, cout, end, ends, overflow_qbit, b_is_bigger)
        _maj_chain_dag(qfun, a, b, cin, mrange)

    for qb in a:
        qfun.apply(X, qb)

    return qfun


@build_gate("MSUB", [int, int, bool, bool])
def subtractor(a_l: int, b_l: int, overflow_qbit=False, little_endian=False) -> QRoutine:
    qfun, a, b, cin, cout, bits, b_is_bigger = _common_init(
        a_l, b_l, overflow_qbit, little_endian
    )
    for qb in a:
        qfun.apply(X, qb)

    mrange, end, ends = _common(qfun, a, b, cout, bits, overflow_qbit)
    if mrange is not None:
        _maj_chain(qfun, a, b, cin, mrange)
        _middle_logic(qfun, a, b, cout, end, ends, overflow_qbit, b_is_bigger)
        _unmaj_chain(qfun, a, b, cin, mrange)
    for qb in itertools.chain(a, b):
        qfun.apply(X, qb)

    return qfun


@build_gate("MADD", [int, int, bool, bool])
def adder(a_l: int, b_l: int, overflow_qbit=False, little_endian=True) -> QRoutine:
    qfun, a, b, cin, cout, bits, b_is_bigger = _common_init(
        a_l, b_l, overflow_qbit, little_endian
    )
    mrange, end, ends = _common(qfun, a, b, cout, bits, overflow_qbit)
    if mrange is None:
        return qfun
    _maj_chain(qfun, a, b, cin, mrange)
    _middle_logic(qfun, a, b, cout, end, ends, overflow_qbit, b_is_bigger)
    _unmaj_chain(qfun, a, b, cin, mrange)

    return qfun


@build_gate("MAJ", [str], arity=lambda _: 3)
def _majority(name: str) -> QRoutine:
    """Majority gate."""
    LOGGER.debug("name %s", name)
    qfun = QRoutine()
    c = qfun.new_wires(1)[0]
    b = qfun.new_wires(1)[0]
    a = qfun.new_wires(1)[0]
    qfun.apply(CNOT, a, b)
    qfun.apply(CNOT, a, c)
    qfun.apply(CCNOT, c, b, a)
    return qfun


@build_gate("UMA", [str], arity=lambda _: 3)
def _unmajority(name: str) -> QRoutine:
    """Unmajority gate."""
    LOGGER.debug("name %s", name)
    qfun = QRoutine()
    c = qfun.new_wires(1)[0]
    b = qfun.new_wires(1)[0]
    a = qfun.new_wires(1)[0]
    qfun.apply(X, b)
    qfun.apply(CNOT, c, b)
    qfun.apply(CCNOT, c, b, a)
    qfun.apply(X, b)
    qfun.apply(CNOT, a, c)
    qfun.apply(CNOT, a, b)
    return qfun


# TODO
@build_gate("HIGH_BIT", [])
def high_bit_only():
    pass

