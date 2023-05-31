from test.common_circuit import CircuitTestCase

from parameterized import parameterized
from qat.external.qroutines import qregs_init as qregs
from qat.external.qroutines.arith import perriello_arith
from qat.lang.AQASM.program import Program


class SArithTestCase(CircuitTestCase):
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
            perriello_arith.LOGGER.setLevel(cls.logger.level)
            for handler in cls.logger.handlers:
                perriello_arith.LOGGER.addHandler(handler)

    @parameterized.expand(
        [
            (0, 0),
            (0, 1),
            (1, 0),
            (1, 1),
        ]
    )
    def test_two_bits_adder(self, a_int, b_int):
        """Add a_int and b_int and check their result.

        The number of bits used to represent the ints is computed at
        runtime.
        """
        # bits = misc.get_required_bits(a_int, b_int)
        self._prepare_adder_circuit(1, 1, True)
        self.logger.debug("a %d", len(self.a))
        self.logger.debug("b %d", len(self.b))

        qfun = qregs.initialize_qureg_given_int(a_int, len(self.a), True)
        self.qc.apply(qfun, self.a)
        qfun = qregs.initialize_qureg_given_int(b_int, len(self.b), True)
        self.qc.apply(qfun, self.b)

        qfun = (~perriello_arith.two_bit_adder)()
        self.qc.apply(qfun, self.a, self.b, self.cout)
        to_measure_qbits = [self.cout[0].index]
        # self.draw_circuit(self.qc)
        to_measure_qbits = [self.cout[0].index, self.b[0].index]

        self.logger.debug("a % s", [qbit.index for qbit in self.a])
        self.logger.debug("b % s", [qbit.index for qbit in self.b])
        self.logger.debug("to measure qubits %s", to_measure_qbits)
        res = self.qpu.submit(self.qc.to_circ().to_job(qubits=to_measure_qbits))
        self.logger.debug("res %s", res)

        counts = len(res)
        self.assertEqual(counts, 1)
        expected = a_int + b_int
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
            (0, 0),
            (0, 1),
            (1, 0),
            (1, 1),
        ]
    )
    def test_two_bits_comparator(self, a_int, b_int):
        """Add a_int and b_int and check their result.

        The number of bits used to represent the ints is computed at
        runtime.
        """
        # bits = misc.get_required_bits(a_int, b_int)
        self._prepare_adder_circuit(1, 1, True)
        self.logger.debug("a %d", len(self.a))
        self.logger.debug("b %d", len(self.b))

        qfun = qregs.initialize_qureg_given_int(a_int, len(self.a), True)
        self.qc.apply(qfun, self.a)
        qfun = qregs.initialize_qureg_given_int(b_int, len(self.b), True)
        self.qc.apply(qfun, self.b)

        qfun = (~perriello_arith.two_bit_comparator)()
        self.qc.apply(qfun, self.a, self.b, self.cout)

        self.logger.debug("a % s", [qbit.index for qbit in self.a])
        self.logger.debug("b % s", [qbit.index for qbit in self.b])
        circ = self.qc.to_circ()
        res = self.qpu.submit(circ.to_job(qubits=self.cout))
        self.logger.debug("res %s", res)

        counts = len(res)
        self.assertEqual(counts, 1)
        expected = int(a_int > b_int)
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
