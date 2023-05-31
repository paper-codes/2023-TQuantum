import itertools
import logging
import unittest
from math import factorial
from test.common_circuit import CircuitTestCase

from qat.external.qroutines.hamming_weight_generate import bartschiE19
from qat.lang.AQASM import Program


class BartschiTestCase(CircuitTestCase):
    @classmethod
    def setUpClass(cls):
        CircuitTestCase.setUpClass()
        bartschi_logger = logging.getLogger(
            "isdquantum.qroutins.hamming_weight_generate.bartschiE19"
        )
        bartschi_logger.setLevel(cls.logger.level)
        bartschi_logger.handlers = cls.logger.handlers

    def _generate_program(self, n, k):
        self.pr = Program()
        qr = self.pr.qalloc(n)
        # pr.apply(dicke_scs(nbqbits), qr)
        self.pr.apply(bartschiE19.generate(n, k), qr)

    def _analyse_res_extensive(self, n, k):
        circ = self.pr.to_circ()
        # self.draw_circuit(circ, max_depth=2)
        res = self.qpu.submit(circ.to_job())
        ress = []
        amps = []
        for sample in res:
            ress.append(tuple(int(i) for i in sample.state if i == 0 or i == 1))
            amps.append(sample.probability)
        s = set(itertools.permutations([0] * (n - k) + [1] * k))
        self.assertEqual(len(ress), len(s))
        for i, j in zip(sorted(ress), sorted(s)):
            self.assertEqual(i, j)
        minp, maxp = min(amps), max(amps)
        self.assertAlmostEqual(minp, maxp, delta=1e-15)
        # self.assertAlmostEqual() abs(minp - maxp) <= 1e-15

    def _analyse_res_quick(self, n, k):
        circ = self.pr.to_circ()
        res = self.qpu.submit(circ.to_job())
        self.assertEqual(len(res), factorial(n) // factorial(k) // factorial(n - k))

    def test_small(self):
        for n, k in itertools.product(range(4, 10), range(1, 4)):
            with self.subTest(n=n, k=k):
                self._generate_program(n, k)
                self._analyse_res_extensive(n, k)

    def test_small_dagger(self):
        for n, k in itertools.product(range(4, 10), range(1, 4)):
            with self.subTest(n=n, k=k):
                self._generate_program(n, k)
                self.pr.apply(bartschiE19.generate(n, k).dag(), self.pr.registers[0])
                circ = self.pr.to_circ()
                res = self.qpu.submit(circ.to_job())
                self.assertEqual(len(res), 1)
                state = res[0].state.state
                self.assertEqual(state, 0)

    # TODO quite useless, just bigger
    @unittest.skipUnless(
        CircuitTestCase.SLOW_TEST_ON, CircuitTestCase.SLOW_TEST_ON_REASON
    )
    def test_bigger(self):
        for n in range(10, 20):
            for k in range(0, int(n / 2)):
                with self.subTest(n=n, k=k):
                    self._generate_program(n, k)
                    self._analyse_res_quick(n, k)
