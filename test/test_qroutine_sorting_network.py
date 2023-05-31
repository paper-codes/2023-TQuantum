import unittest
from test.common_circuit import CircuitTestCase

from parameterized import parameterized
# # from qat.external.qpus.reversible import RProgram
from qat.external.qroutines import qregs_init as qregs
from qat.external.qroutines.sorting import sorting_network as sn
from qat.lang.AQASM.program import Program


class SortingNetworkTestCase(CircuitTestCase):
    LITTLE_ENDIAN = False

    @classmethod
    def _check_bitonic(cls, string):
        monotonicity_changes = 0
        for i in range(1, len(string)):
            if string[i] < string[i - 1] or string[i] > string[i - 1]:
                monotonicity_changes += 1
            if monotonicity_changes > 2:
                return False
        return True

    @classmethod
    def _check_halves_sorted(cls, string):
        halflen = int(len(string) / 2)
        st1, st2 = string[:halflen], string[halflen : halflen * 2]

        is_sorted_1 = all(st1[i] <= st1[i + 1] for i in range(halflen - 1))

        res = is_sorted_1 and all(st2[i] <= st2[i + 1] for i in range(halflen - 1))
        if not res:
            raise Exception(f"Halves not sorted {string}")

    def _prepare_circuit(self, string, pattern):
        self.pr = Program()
        self.qr = self.pr.qalloc(pattern["n_lines"])
        self.comps = self.pr.qalloc(pattern["n_comps"])
        init = qregs.initialize_qureg_given_bitstring(string, self.LITTLE_ENDIAN)
        self.pr.apply(init, self.qr)

    def _simulate_and_check_result(self, string: str, expected: str, check_sorted=True):
        obtained = self._simulate_and_get_result()
        if not obtained:
            raise Exception(f"Unknown flow")
        is_sorted = all(obtained[i] <= obtained[i + 1] for i in range(len(string) - 1))
        if check_sorted:
            self.assertTrue(is_sorted)
            self.assertEqual(obtained, expected)

    def _simulate_and_get_result(self):
        obtained = None
        if self.REVERSIBLE_ON:
            cr = self.pr.to_circ(include_matrices=False, submatrices_only=True)
            rpr = RProgram.circuit_to_rprogram(cr)
            qridxs = [qbit.index for qbit in self.qr]
            obtained = "".join(
                [str(bit) for i, bit in enumerate(rpr.rbits) if i in qridxs]
            )
        else:
            res = self.simulate_program(self.pr, job_args={"qubits": self.qr})
            i = -1
            for i, sample in enumerate(res):
                obtained = sample.state.bitstring
                if self.SIMULATOR == "linalg":
                    self.assertEqual(sample.probability, 1)
            self.assertEqual(i, 0)
        return obtained

    def _test_sorter_common(self, string):
        n = len(string)
        pattern = sn.get_pattern_sorter(n)

        self._prepare_circuit(string, pattern)

        qrout = sn.build_gate_sorter(pattern)
        self.pr.apply(qrout, self.qr, self.comps)
        sorted_string_exp = "".join(list(sorted(string)))

        self._simulate_and_check_result(string, sorted_string_exp)

    @parameterized.expand(
        [
            "0000",
            "1111",
            "0110",
            "1010",
            "10010000",
            "11000011",
        ]
    )
    def test_bitonic_sorter(self, string):
        is_bitonic = self._check_bitonic(string)
        n = len(string)
        # print(is_bitonic)
        pattern = sn.get_pattern_bitonic_sorter(n)
        self._prepare_circuit(string, pattern)

        qrout = sn.build_gate_bitonic_sorter(pattern)
        self.pr.apply(qrout, self.qr, self.comps)

        sorted_string_exp = "".join(list(sorted(string)))
        self._simulate_and_check_result(string, sorted_string_exp, is_bitonic)

    @parameterized.expand(
        [
            "01",
            "10",
            "0000",
            "1111",
            "0101",
            "1101",
            "00110111",
        ]
    )
    def test_merger(self, string):
        self._check_halves_sorted(string)
        n = len(string)
        pattern = sn.get_pattern_merger(n)
        self._prepare_circuit(string, pattern)

        qrout = sn.build_gate_merger(pattern)
        self.pr.apply(qrout, self.qr, self.comps)

        sorted_string_exp = "".join(list(sorted(string)))
        self._simulate_and_check_result(string, sorted_string_exp)

    @parameterized.expand(
        [
            "01",
            "10",
            "0000",
            "1111",
            "0001",
            "0010",
            "0111",
            "1011",
            "1001",
        ]
    )
    def test_sorter(self, string):
        self._test_sorter_common(string)

    @parameterized.expand(
        [
            "10110111",
        ]
    )
    @unittest.skipUnless(
        (CircuitTestCase.SLOW_TEST_ON and CircuitTestCase.QLM_ON)
        or (CircuitTestCase.REVERSIBLE_ON),
        f"Either {CircuitTestCase.SLOW_TEST_ON_REASON} or"
        f" {CircuitTestCase.QLM_ON_REASON}",
    )
    def test_sorter_qlm(self, string):
        self._test_sorter_common(string)

    @parameterized.expand(
        [
            "10110111111100110101000110100011",
        ]
    )
    @unittest.skipUnless(CircuitTestCase.REVERSIBLE_ON, f"Only with reversible")
    def test_sorter_long(self, string):
        self._test_sorter_common(string)
