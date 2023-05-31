import itertools
from test.common_circuit import CircuitTestCase

from parameterized import parameterized
# from qat.external.qpus.reversible import RProgram
from qat.external.qroutines import qregs_init as qregs
from qat.external.qroutines.arith import cuccaro_arith
from qat.external.utils.bits import conversion, misc
from qat.lang.AQASM.program import Program


class AdderTestCase(CircuitTestCase):
    def _prepare_adder_circuit(self, a_bits, b_bits, overflow=True):
        self.qc = Program()
        if a_bits > 0:
            self.a = self.qc.qalloc(a_bits)
        if b_bits > 0:
            self.b = self.qc.qalloc(b_bits)
        if overflow:
            self.cout = self.qc.qalloc(1)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.logger.level != 0:
            cuccaro_arith.LOGGER.setLevel(cls.logger.level)
            for handler in cls.logger.handlers:
                cuccaro_arith.LOGGER.addHandler(handler)

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
        ]
    )
    def test_adder(self, a_int, b_int):
        """Add a_int and b_int and check their result.

        The number of bits used to represent the ints is computed at
        runtime.
        """
        bits = misc.get_required_bits(a_int, b_int)
        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                # Bcz a and b must have the same size
                self._prepare_adder_circuit(bits, bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))
                self.logger.debug("little endian %s", little_endian)
                self.logger.debug("overflow %s", overflow)

                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)
                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun, self.b)

                qfun = (~cuccaro_arith.adder)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                    # self.draw_circuit(self.qc)
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun, self.a, self.b)
                    # self.draw_circuit(self.qc,
                    # circuit_name=f"{little_endian}")
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
                cr = self.qc.to_circ()

                expected = a_int + b_int
                if not overflow:
                    expected %= 2**bits
                # expected_str = conversion.get_bitstring_from_int(
                #     expected, len(to_measure_qbits))
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
            (3, 2),
            (7, 9),
            (15, 7),
            (15, 1),
            (24, 7),
        ]
    )
    def test_adder_inverse(self, a_int, b_int):
        """Test the adder + adder_inverse.

        The output should be equal to the original state of the circuit.
        """
        bits = misc.get_required_bits(a_int, b_int)
        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                # Bcz a and b must have the same size
                self._prepare_adder_circuit(bits, bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))

                qfun1 = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun1, self.a)
                qfun2 = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun2, self.b)

                qfun3 = (~cuccaro_arith.adder)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun3, self.a, self.b, self.cout)
                    self.qc.apply(qfun3.dag(), self.a, self.b, self.cout)
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun3, self.a, self.b)
                    self.qc.apply(qfun3.dag(), self.a, self.b)
                self.qc.apply(qfun2.dag(), self.b)
                self.qc.apply(qfun1.dag(), self.a)

                cr = self.qc.to_circ()
                expected = 0
                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    bits = rpr.rbits.to01()
                    self.assertEqual(int(bits, 2), expected)
                    return
                res = self.qpu.submit(cr.to_job())
                self.logger.debug("res %s", res)

                counts = len(res)
                self.assertEqual(counts, 1)
                state = res[0].state

                self.logger.debug("expected %d, having %d", expected, state.state)
                self.assertEqual(state.state, expected)

    @parameterized.expand(
        [
            (1, 3),
            (2, 4),
            (2, 9),
            (7, 9),
            (7, 15),
            (1, 15),
            (2, 33),
        ]
    )
    def test_adder_different_size_b_bigger(self, a_int, b_int):
        """Test the adder when the output reg is bigger than the other one."""
        a_bits = misc.get_required_bits(a_int)
        b_bits = misc.get_required_bits(b_int)
        if a_bits == b_bits:
            raise ValueError(
                f"We are testing for b_bigger, while a={a_int} and b={b_int}"
            )

        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                self._prepare_adder_circuit(a_bits, b_bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))
                self.logger.debug("little endian %s", little_endian)
                self.logger.debug("overflow %s", overflow)
                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)
                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun, self.b)

                qfun = (~cuccaro_arith.adder)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun, self.a, self.b)
                    to_measure_qbits = []

                if little_endian:
                    self.logger.debug("little endian")
                    to_measure_qbits += [qbit.index for qbit in reversed(self.b)]
                else:
                    self.logger.debug("big endian")
                    to_measure_qbits += [qbit.index for qbit in self.b]

                cr = self.qc.to_circ()
                expected = a_int + b_int
                # if not overflow:
                # It also happen with overflow
                expected %= 2 ** len(to_measure_qbits)

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
            (4, 1),
            (15, 1),
            (24, 7),
            (24, 11),
            (33, 1),
            (33, 2),
        ]
    )
    def test_adder_different_size_a_bigger(self, a_int, b_int):
        """Test the adder when the output reg is smaller than the other one."""
        a_bits = misc.get_required_bits(a_int)
        b_bits = misc.get_required_bits(b_int)
        if a_bits == b_bits:
            raise ValueError(
                f"We are testing for a_bigger, while a={a_int} and b={b_int}"
            )

        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                self._prepare_adder_circuit(a_bits, b_bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))
                self.logger.debug("little endian %s", little_endian)
                self.logger.debug("overflow %s", overflow)
                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)
                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun, self.b)

                qfun = (~cuccaro_arith.adder)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun, self.a, self.b)
                    to_measure_qbits = []

                if little_endian:
                    self.logger.debug("little endian")
                    to_measure_qbits += [qbit.index for qbit in reversed(self.b)]
                else:
                    self.logger.debug("big endian")
                    to_measure_qbits += [qbit.index for qbit in self.b]

                expected = a_int + b_int
                # It also happen with overflow
                expected %= 2 ** len(to_measure_qbits)

                cr = self.qc.to_circ()
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
            (3, 2),
            (5, 4),
            (5, 3),
            (7, 3),
            (7, 5),
        ]
    )
    def test_halves_sum(self, a_int, bits):
        """Add two halves of a register on a given number of bits."""
        if bits % 2 == 1:
            bits = bits + 1
        self.logger.debug("n bits = %s", bits)
        misc.assert_enough_bits(a_int, bits)
        half_bits = int(bits / 2)
        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                self._prepare_adder_circuit(bits, 0, overflow)

                # Initialize a to its value
                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)
                qfun = (~cuccaro_arith.adder)(
                    half_bits, bits - half_bits, overflow, little_endian
                )
                term1 = [self.a[i] for i in range(half_bits)]
                term2 = [self.a[i] for i in range(half_bits, bits)]

                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun, term1, term2, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun, term1, term2)
                    to_measure_qbits = []

                if little_endian:
                    self.logger.debug("little endian")
                    to_measure_qbits += [qbit.index for qbit in reversed(term2)]
                else:
                    self.logger.debug("big endian")
                    to_measure_qbits += [qbit.index for qbit in term2]

                a_str = conversion.get_bitstring_from_int(a_int, bits, little_endian)
                term1_int = conversion.get_int_from_bitstring(
                    a_str[0:half_bits], little_endian
                )
                term2_int = conversion.get_int_from_bitstring(
                    a_str[half_bits:bits], little_endian
                )
                expected = term1_int + term2_int
                expected %= 2 ** len(to_measure_qbits)

                cr = self.qc.to_circ()
                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    bitstring = "".join(
                        [str(rpr.rbits[index]) for index in to_measure_qbits]
                    )
                    bits = int(bitstring, 2)
                    self.assertEqual(bits, expected)
                    return

                res = self.qpu.submit(self.qc.to_circ().to_job(qubits=to_measure_qbits))
                self.logger.debug("res %s", res)

                counts = len(res)
                self.assertEqual(counts, 1)

                self.logger.debug("a_str %s", a_str)
                self.logger.debug("a first half %s", term1_int)
                self.logger.debug("a second half %s", term2_int)
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
            # a > b case
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
        bits = misc.get_required_bits(a_int, b_int)
        for little_endian, overflow in itertools.product((True, False), (True, False)):
            with self.subTest(little_endian=little_endian, overflow=overflow):
                # Bcz a and b must have the same size
                self._prepare_adder_circuit(bits, bits, overflow)
                self.logger.debug("a %d", len(self.a))
                self.logger.debug("b %d", len(self.b))
                self.logger.debug("little endian %s", little_endian)
                self.logger.debug("overflow %s", overflow)

                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)
                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun, self.b)

                qfun = (~cuccaro_arith.subtractor)(
                    len(self.a), len(self.b), overflow, little_endian
                )
                if overflow:
                    self.logger.debug("overflow")
                    self.qc.apply(qfun, self.a, self.b, self.cout)
                    to_measure_qbits = [self.cout[0].index]
                else:
                    self.logger.debug("no overflow")
                    self.qc.apply(qfun, self.a, self.b)
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

                cr = self.qc.to_circ()
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
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 4),
            (5, 5),
            (6, 4),
            (7, 9),
            (8, 15),
            (9, 9),
        ]
    )
    def test_a_smaller_than_b(self, a_int, b_int):
        """Test that a is smaller than b and, if that is the case, store 1 in
        cout."""
        # Prepare qubits
        bits = misc.get_required_bits(a_int, b_int)
        self.logger.debug("n bits = %s", bits)
        for little_endian in (True, False):
            with self.subTest(little_endian=little_endian):
                self._prepare_adder_circuit(bits, bits, True)

                qfun = qregs.initialize_qureg_given_int(
                    a_int, len(self.a), little_endian
                )
                self.qc.apply(qfun, self.a)

                qfun = qregs.initialize_qureg_given_int(
                    b_int, len(self.b), little_endian
                )
                self.qc.apply(qfun, self.b)

                qfun = (~cuccaro_arith.comparator)(bits, bits, little_endian)
                self.qc.apply(qfun, self.a, self.b, self.cout)

                expected = 1 if a_int < b_int else 0

                cr = self.qc.to_circ()
                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    # bitstring = "".join([str(rpr.rbits[index]) for index in to_measure_qbits])
                    bitstring = rpr.rbits.to01()[self.cout[0].index]
                    bits = int(bitstring, 2)
                    self.assertEqual(bits, expected)
                    return

                res = self.qpu.submit(cr.to_job(qubits=[self.cout]))
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
                    actual = res[0].state.state
                    self.logger.debug("expected %s, actual %s", expected, actual)
                    self.assertEqual(actual, expected)
