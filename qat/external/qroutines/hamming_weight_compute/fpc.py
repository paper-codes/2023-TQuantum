import logging
from math import ceil, log
from typing import TYPE_CHECKING

from qat.lang.AQASM.routines import QRoutine
from qat.lang.AQASM.gates import X
from qat.lang.AQASM.misc import build_gate

from qat.external.utils.bits import conversion
from qat.external.qroutines.arith import cuccaro_arith as adder
from qat.external.qroutines import qregs_init as qregs

if TYPE_CHECKING:
    from qat.lang.AQASM.bits import QRegister

LOGGER = logging.getLogger(__name__)


@build_gate("FPC_WCOM", [int, int, dict])
def get_qroutine_for_qubits_weight(a_len: int, cout_len: int, patterns_dict: dict):
    """QRoutine to compute the hamming weight of a set of qubits.

    The patterns_dict must be computed in advance by the :func:
    `~get_qroutine_for_qubits_weight_get_pattern`. This will help to
    have a precise estimate of the number of qbits and gates that will
    be required.
    """

    assert a_len == patterns_dict["n_lines"]
    assert cout_len == patterns_dict["n_couts"]

    qfun = QRoutine()
    a_qs = qfun.new_wires(a_len)
    cout_qs = qfun.new_wires(cout_len)
    LOGGER.debug("a %s", a_qs)
    LOGGER.debug("cout %s", cout_qs)

    for i in patterns_dict["adders_pattern"]:
        cout_idx = int(i[-1][1:])
        half_bits = int((len(i) - 1) / 2)
        input_qubits = []
        for j in i:
            if j[0] == "a":
                input_qubits.append(a_qs[int(j[1:])])
            elif j[0] == "c":
                input_qubits.append(cout_qs[int(j[1:])])
            else:
                raise ValueError(
                    "Invalid data in patterns_dict, has it been generated"
                    "using the get_pattern() routine?"
                )
        tmp_a = [input_qubits[i] for i in range(half_bits)]
        tmp_b = [input_qubits[i] for i in range(half_bits, 2 * half_bits)] + [
            cout_qs[cout_idx]
        ]
        LOGGER.debug("%s", tmp_a)
        LOGGER.debug("%s", tmp_b)

        # tmp_b - 1 bcz we also added the cout in tmp_b
        qfun_add = (~adder.adder)(len(tmp_a), len(tmp_b) - 1, True, True)
        qfun.apply(qfun_add, tmp_a, tmp_b)
    return qfun


def get_to_measure_qubits(a_qs: "QRegister", cout_qs: "QRegister", patterns_dict: dict):
    """It returns the list of qbits containing the final result."""
    to_measure_qubits = []
    for j in patterns_dict["results"]:
        if j[0] == "a":
            to_measure_qubits.append(a_qs[int(j[1:])])
        elif j[0] == "c":
            to_measure_qubits.append(cout_qs[int(j[1:])])
        else:
            raise ValueError(
                "Invalid data in patterns_dict, has it been generated"
                "using the get_pattern() routine?"
            )
    return to_measure_qubits


def get_qroutine_for_qubits_weight_get_pattern(n):
    """Given n bits, it returns a dictionary containing the pattern to compute
    the weight of this n bits, ie:

    #. n_lines: required qubits (>= n, the closest power of 2) #.
    n_couts, the total number of couts required by the adders #.
    adders_pattern, the pattern of adders #. results, the bits
    containing the final results
    """
    steps = ceil(log(n, 2))
    # TODO maybe we can use fewer lines
    n_lines = 2**steps
    patterns_dict = {}
    patterns_dict["n_lines"] = n_lines
    patterns_dict["n_couts"] = n_lines - 1
    couts = ["c{0}".format(i) for i in range(patterns_dict["n_couts"])][::-1]
    inputs = ["a{0}".format(i) for i in range(patterns_dict["n_lines"])][::-1]
    LOGGER.debug("inputs %s", inputs)
    LOGGER.debug("couts %s", couts)
    patterns_dict["adders_pattern"] = []

    n_adders = n_lines
    n_inputs_per_adders = 0
    inputs_next_stage = inputs
    for i in range(steps):
        n_adders = int(n_adders / 2)
        n_inputs_per_adders += 2
        outputs_this_stage = []
        LOGGER.debug(
            "Stage %d, n_adder %d, n_inputs_per_adder %d",
            i,
            n_adders,
            n_inputs_per_adders,
        )
        LOGGER.debug("inputs_next_stage %s", inputs_next_stage)
        for j in range(n_adders):
            LOGGER.debug("Stage %d, adder %d", i, j)
            adder_inputs = []
            for k in range(n_inputs_per_adders):
                adder_inputs.append(inputs_next_stage.pop())
            adder_cout = couts.pop()
            adder_outputs = adder_inputs[
                int(len(adder_inputs) / 2) : len(adder_inputs)
            ] + [adder_cout]
            patterns_dict["adders_pattern"].append(
                tuple(adder_inputs) + tuple([adder_cout])
            )
            LOGGER.debug("%s, %s --> %s", adder_inputs, adder_cout, adder_outputs)
            outputs_this_stage += adder_outputs
        inputs_next_stage = outputs_this_stage[::-1]
    LOGGER.debug("adders pattern\n%s", patterns_dict["adders_pattern"])
    patterns_dict["results"] = inputs_next_stage[::-1]
    LOGGER.debug("results\n%s", patterns_dict["results"])
    return patterns_dict


# def get_qroutine_for_qubits_weight_check(circuit, a_qs, cin_q, cout_qs, eq_q,
#                                          anc_q, weight_int, patterns_dict):
@build_gate("FPC_WCHE", [int, int, int, dict, bool])
def get_qroutine_for_qubits_weight_check(
    a_l, cout_l, weight_int, patterns_dict, compute_eq
):
    """Circuit to check if a given set of register (a_qs) has weight equal to
    weight_int. In this case, eq is set to 1. The compute_eq flag is
    particularly useful if we want to use a compute-uncompute pattern, while
    still leaving the eq qubit untouched. In other words, the flow will be.

    1. apply weight_check(True)
    2. apply weight_checl(False).dag()

    In this way, all the qubits are restored, except for the eq qubit.

    Another possible use case is when we want to use not only the result qubits
    of this function, but also other qubits, as control ones. For example if,
    in addition to the weight being equal to a specific int, we also have to
    check for additional features coming from other parts of the circuit.
    """
    circuit = QRoutine()
    a_qs = circuit.new_wires(a_l)
    cout_qs = circuit.new_wires(cout_l)
    if compute_eq:
        eq_q = circuit.new_wires(1)
    else:
        eq_q = None
    equal_str = conversion.get_bitstring_from_int(
        weight_int, len(patterns_dict["results"]), True
    )
    LOGGER.debug("equal_str %s", equal_str)

    qfun = (~get_qroutine_for_qubits_weight)(a_l, cout_l, patterns_dict)
    circuit.apply(qfun, a_qs, cout_qs)
    result_qubits = get_to_measure_qubits(a_qs, cout_qs, patterns_dict)
    # We already have the string in little endian, so we don't have to reverse
    # it again
    qfun = qregs.initialize_qureg_to_complement_of_bitstring(equal_str, False)
    circuit.apply(qfun, result_qubits)

    if compute_eq:
        set_qubit_if_true(a_qs, cout_qs, patterns_dict, eq_q, circuit)
    return circuit


def set_qubit_if_true(a_qs, cout_qs, patterns_dict, eq_q, circuit):
    result_qubits = get_to_measure_qubits(a_qs, cout_qs, patterns_dict)
    ctrls = [qb for qb in result_qubits]
    circuit.apply(X.ctrl(len(ctrls)), ctrls, eq_q[0])
