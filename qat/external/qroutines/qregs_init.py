"""Notes on endianness convention. Most quantum toolkits use little-endianness;
that is, a 3 qubit register |a \otimes b \otimes c> has qreg[0] = c, qreg[1] =
b, qreg[2] = a.

In myqlm, on the other hand, if qreg[0]=1, qreg[1]=0, qreg[2]=0, the output
will be |100>. So it can be thougth as big-endianness.

"""
import functools
import logging
from typing import TYPE_CHECKING, List, Sequence

from qat.external.utils.bits import conversion
from qat.lang.AQASM.gates import X
from qat.lang.AQASM.misc import build_gate
from qat.lang.AQASM.routines import QRoutine

if TYPE_CHECKING:
    from qat.lang.AQASM.bits import QRegister

LOGGER = logging.getLogger(__name__)

# In big endian the MSB is on the left, while the LSB is on the right. So in
# big endian |100> would be equal to 4, while in little endian it will be equal
# to 1. Big endian is used by both ibm's qiskit and atos' qlm results. However,
# Atos qlm uses little endian for all other stuffs


# Little endian in qubit initialization also means left-to-right bitstring
# corresponds bottom-to-top in circuit
@build_gate("QBIT_INIT", [Sequence, int, bool], lambda x, y, _: len(x) + y)
def _conditionally_initialize_qureg_given_bitarray(
    a_arr: Sequence[int],
    ncontrols: int,
    little_endian: bool,
) -> QRoutine:
    """The input array should be in BIG ENDIAN notation, meaning that an array
    with 4 elements, say 'abcd', has array[0]=a, array[1]=b, .... On the other
    hand, you can decide on the endianness of the qubit, i.e., how the values
    will be stored inside qureg. If you choose big-endian, qreg[0] = a, qreg[1]
    = b, ...; if you choose little-endian, qreg[0] = d, qreg[1] = c, ...

    :param a_arr: a sequence of bits, in BIG ENDIAN
    :param little_endian: whether to initialize the qubits in little endian or not

    """
    qr = QRoutine()
    bits = qr.new_wires(len(a_arr))
    gate = X

    if ncontrols > 0:
        # for _ in range(len(qcontrols)):
        gate = gate.ctrl(ncontrols)
    part = functools.partial(qr.apply, gate)

    if ncontrols > 0:
        cbits = qr.new_wires(ncontrols)
        part = functools.partial(part, *cbits)

    mrange = zip(bits, reversed(a_arr)) if little_endian else zip(bits, a_arr)
    for qbit, aint in mrange:
        if aint == 1:
            part(qbit)
        elif aint != 0:
            err_mes = "string %s contains non-binary value %s" % (a_arr, aint)
            raise ValueError(err_mes)
    return qr


def conditionally_initialize_qureg_given_bitarray(
    a_arr: Sequence[int],
    ncontrols: "QRegister",
    little_endian,
) -> QRoutine:
    return _conditionally_initialize_qureg_given_bitarray(
        a_arr, ncontrols, little_endian
    )


def conditionally_initialize_qureg_given_bitstring(
    a_str, ncontrols, little_endian
) -> QRoutine:
    a_list = [int(c) for c in a_str]
    # a_list = map(int, a_str)
    return _conditionally_initialize_qureg_given_bitarray(
        a_list, ncontrols, little_endian
    )


def conditionally_initialize_qureg_to_complement_of_bitstring(
    a_str, ncontrols, little_endian
) -> QRoutine:
    a_n_str = conversion.get_negated_bistring(a_str)
    return conditionally_initialize_qureg_given_bitstring(
        a_n_str, ncontrols, little_endian
    )


def conditionally_initialize_qureg_to_complement_of_bitarray(
    a_str, ncontrols, little_endian
) -> QRoutine:
    a_n_str = conversion.get_negated_bitarray(a_str)
    return _conditionally_initialize_qureg_given_bitarray(
        a_n_str, ncontrols, little_endian
    )


# @build_gate("QBIT_INIT_BITA", [Union[List, nptyping.NDArray], bool])
# @build_gate("QBIT_INIT_BITA", [List, bool])
def initialize_qureg_given_bitarray(a_str, little_endian) -> QRoutine:
    """Given a binary string (in BIG ENDIAN), initialize the qreg to the proper
    value corresponding to it. Basically, if a_str is 1011, meaning a_str[0] =
    1, a_str[1] = 0, ..., and little_endian is False, the function negate bits
    0, 2 and 3. If little_endian is True, it negates bits 0, 1 and 3.


    :param a_str: the binary digits bit string
    :param qreg: the QuantumRegister on which the integer should be set
    :param circuit: the QuantumCircuit containing the q_reg

    :return False if no operation was performed, True if at least one operation
    was performed

    """
    return _conditionally_initialize_qureg_given_bitarray(a_str, 0, little_endian)


def initialize_qureg_given_bitstring(a_str, little_endian) -> QRoutine:
    """Given a binary string, initialize the qreg to the proper value
    corresponding to it. Basically, if a_str is 1011, the function negate bits
    0, 1 and 3 of the qreg. # 3->0; 2->1; 1->2; 0;3 Note that the qreg has the
    most significant bit in the rightmost part (little endian) of the qreg,
    i.e. the most significant bit is on qreg 0. In the circuit, it means that
    the most significant bits are the lower ones of the qreg.

    :param a_str: the binary digits bit string
    :param qreg: the QuantumRegister on which the integer should be set
    :param circuit: the QuantumCircuit containing the q_reg

    :return False if no operation was performed, True if at least one operation
    was performed
    """
    return conditionally_initialize_qureg_given_bitstring(a_str, 0, little_endian)


def initialize_qureg_given_int(a_int, n_bits, little_endian):
    """Given a decimal integer, initialize the qreg to the proper value
    corresponding to it. Basically, if a_int is 11, i.e. 1011 in binary, the
    function negate bits 3, 2 and 0 of the qreg. Note that the qreg has the
    most significant bit in the leftmost part (big endian)

    :param a_int: the integer in decimal base
    :param qreg: the QuantumRegister on which the integer should be set
    :param circuit: the QuantumCircuit containing the q_reg
    """
    a_str = conversion.get_bitstring_from_int(a_int, n_bits)
    return initialize_qureg_given_bitstring(a_str, little_endian)


# I.e. if bitstring is 1011, it initializes the qreg to 0100
def initialize_qureg_to_complement_of_bitstring(a_str, little_endian):
    a_n_str = conversion.get_negated_bistring(a_str)
    return initialize_qureg_given_bitstring(a_n_str, little_endian)


def initialize_qureg_to_complement_of_bitarray(a_arr, little_endian):
    a_n_str = conversion.get_negated_bitarray(a_arr)
    return initialize_qureg_given_bitstring(a_n_str, little_endian)


def initialize_qureg_to_complement_of_int(a_int, n_bits, little_endian):
    a_str = conversion.get_bitstring_from_int(a_int, n_bits)
    return initialize_qureg_to_complement_of_bitstring(a_str, little_endian)
