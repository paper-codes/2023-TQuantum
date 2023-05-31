from test.common_circuit import CircuitTestCase

from parameterized import parameterized
# from qat.external.qpus.reversible import RProgram
from qat.external.qroutines import qregs_init as qregs
from qat.external.qroutines.arith import tkk_arith
from qat.external.utils.bits import misc
from qat.lang.AQASM.program import Program


class AdderTestCase(CircuitTestCase):
    def _prepare_adder_circuit(self, a_bits, b_bits, overflow):
        self.pr = Program()
        if a_bits > 0:
            self.a = self.pr.qalloc(a_bits)
        if b_bits > 0:
            self.b = self.pr.qalloc(b_bits)
        if overflow:
            self.cout = self.pr.qalloc(1)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.logger.level != 0:
            tkk_arith.LOGGER.setLevel(cls.logger.level)
            for handler in cls.logger.handlers:
                tkk_arith.LOGGER.addHandler(handler)

    @parameterized.expand(
        [
            (1, 1),
            (3, 2),
            (3, 1),
            (2, 0),
            (7, 9),
            (9, 5),
            (15, 11),
            (15, 1),
            (24, 7),
            (124, 77),
        ]
    )
    def test_adder(self, a_int, b_int):
        """Add a_int and b_int and check their result.

        The number of bits used to represent the ints is computed at
        runtime.
        """
        little_endian = True
        bits = misc.get_required_bits(a_int, b_int)
        # for overflow in itertools.product((True, False), (True, False)):
        for overflow in (True, False):
            with self.subTest(overflow=overflow):
                self._prepare_adder_circuit(bits, bits, overflow)

                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.pr.apply(qfun, self.a)

                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.pr.apply(qfun, self.b)

                # qfun = (~tkk_arith.adder)(len(self.a), len(self.b), overflow, little_endian)
                qfun = (~tkk_arith.adder)(bits, bits, overflow, little_endian)
                if overflow:
                    self.pr.apply(qfun, self.a, self.b, self.cout)
                    self.logger.debug("overflow")
                    # self.pr.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.pr.apply(qfun, self.a, self.b)
                    self.logger.debug("no overflow")
                    # self.pr.apply(qfun, self.a, self.b)
                    to_measure_qbits = []
                if little_endian:
                    self.logger.debug("little endian")
                    to_measure_qbits += [qbit.index for qbit in reversed(self.b)]
                else:
                    self.logger.debug("big endian")
                    to_measure_qbits += [qbit.index for qbit in self.b]

                self.logger.debug("a % s", [qbit.index for qbit in self.a])
                self.logger.debug("b % s", [qbit.index for qbit in self.b])
                if overflow:
                    self.logger.debug("cout %d", self.cout[0].index)
                self.logger.debug("to measure qubits %s", to_measure_qbits)
                cr = self.pr.to_circ()

                expected = a_int + b_int
                if not overflow:
                    expected %= 2**bits

                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    bitstring = "".join(
                        [str(rpr.rbits[index]) for index in to_measure_qbits]
                    )
                    bits = int(bitstring, 2)
                    self.assertEqual(bits, expected)
                    return

                res = self.qpu.submit(cr.to_job(qubits=to_measure_qbits))
                self.logger.debug("res %s", res)
                counts = len(res)
                self.assertEqual(counts, 1)
                if self.SIMULATOR == "linalg":
                    # For QLM
                    for sample in res:
                        if sample.state.lsb_int == expected:
                            self.assertEqual(sample.probability, 1)
                            break
                elif self.SIMULATOR == "pylinalg":
                    # myQLM
                    state = res[0].state
                    self.assertEqual(state.state, expected)

    @parameterized.expand(
        [
            (1, 1),
            (3, 2),
            (3, 1),
            (2, 0),
            (9, 5),
            (15, 11),
            (15, 1),
            # # a > b case
            (24, 7),
            (7, 9),
            (3, 6),
            (2, 10),
        ]
    )
    def test_subtractor(self, a_int, b_int):
        """
        Execute a_int - b_int and check their result.
        The number of bits used to represent the ints is computed at runtime.
        """
        little_endian = True
        bits = misc.get_required_bits(a_int, b_int)
        # for overflow in itertools.product((True, False), (True, False)):
        for overflow in (True, False):
            with self.subTest(overflow=overflow):
                # Bcz a and b must have the same size
                self._prepare_adder_circuit(bits, bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))
                self.logger.debug("little endian %s", little_endian)
                self.logger.debug("overflow %s", overflow)

                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.pr.apply(qfun, self.a)
                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.pr.apply(qfun, self.b)

                qfun = (~tkk_arith.subtractor)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.pr.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.logger.debug("no overflow")
                    self.pr.apply(qfun, self.a, self.b)
                    to_measure_qbits = []
                if little_endian:
                    self.logger.debug("little endian")
                    to_measure_qbits += [qbit.index for qbit in reversed(self.b)]
                else:
                    self.logger.debug("big endian")
                    to_measure_qbits += [qbit.index for qbit in self.b]

                self.logger.debug("a % s", [qbit.index for qbit in self.a])
                self.logger.debug("b % s", [qbit.index for qbit in self.b])
                if overflow:
                    self.logger.debug("cout %d", self.cout[0].index)
                self.logger.debug("to measure qubits %s", to_measure_qbits)

                expected = a_int - b_int
                if expected < 0:
                    expected = 2 ** len(to_measure_qbits) + expected
                if not overflow:
                    expected %= 2**bits

                cr = self.pr.to_circ()
                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    bitstring = "".join(
                        [str(rpr.rbits[index]) for index in to_measure_qbits]
                    )
                    bits = int(bitstring, 2)
                    self.assertEqual(bits, expected)
                    return

                res = self.qpu.submit(cr.to_job(qubits=to_measure_qbits))
                self.logger.debug("res %s", res)

                counts = len(res)
                self.assertEqual(counts, 1)
                if self.SIMULATOR == "linalg":
                    # For QLM
                    for sample in res:
                        if sample.state.lsb_int == expected:
                            self.assertEqual(sample.probability, 1)
                            break
                elif self.SIMULATOR == "pylinalg":
                    # myQLM
                    state = res[0].state
                    self.assertEqual(state.state, expected)
