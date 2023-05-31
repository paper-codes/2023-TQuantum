import unittest
from test.common_circuit import CircuitTestCase

import numpy as np
from parameterized import parameterized
# from qat.external.qpus.reversible import RProgram
from qat.external.qroutines.linalg import gauss_jordan_isd4 as gji
from qat.external.qroutines.linalg import matrix as qmatrix
from qat.lang.AQASM.program import Program
from sympy import Matrix


class GjiTestCase(CircuitTestCase):
    def _prepare_circuit(self, matrix):
        pr = Program()
        nrows, ncols = matrix.shape

        qrout = qmatrix.initialize_qureg_to_binary_matrix(matrix)
        qr_matrix = pr.qalloc(nrows * ncols)
        pr.apply(qrout, qr_matrix)
        qregs_rows = qmatrix.get_rows_as_qubit_list(nrows, ncols, qr_matrix)

        qbit_range = set(q.index for qreg in qregs_rows for q in qreg)
        swap_anc_n, add_anc_n = gji.get_required_ancillae(nrows)
        swap_qregs = pr.qalloc(swap_anc_n)
        if add_anc_n > 0:
            add_qregs = pr.qalloc(add_anc_n)
            raise Exception("Unhandled")
        else:
            add_qregs = None
        return pr, qregs_rows, add_qregs, swap_qregs, qbit_range

    def _common_test(
        self,
        matrix,
        test_u,
        should_iden,
    ):
        """:param test_u: build u from ancillae and check it's correct
        :param should_iden: we are checking that the procedure gives an identity matrix. Note that, if skip_rightmost is true, we do not have exactly an identity matrix, but still the diagonal elements are all 1 and the bottom-left submatrix below the diagonal is all zero
        """
        r, n = matrix.shape
        nrows = r
        syndrome = np.random.randint(0, 2, size=(nrows, 1))
        # 1 syndrome
        ncols = n + 1
        # concatenate the syndrome to the original matrix
        matrix_ext = np.hstack((matrix, syndrome))
        skip_rightmost_val = (False,) if r == n else (False, True)

        for skip_rightmost in skip_rightmost_val:
            with self.subTest(skip_rightmost=skip_rightmost):
                (
                    pr,
                    qregs_rows,
                    add_qregs,
                    swap_qregs,
                    qbit_range,
                ) = self._prepare_circuit(matrix_ext)
                gji_gate = gji.get_rref(nrows, ncols, skip_rightmost, n)
                if add_qregs:
                    pr.apply(gji_gate, qregs_rows, swap_qregs, add_qregs)
                else:
                    pr.apply(gji_gate, qregs_rows, swap_qregs)

                cr = pr.to_circ()
                if self.REVERSIBLE_ON:
                    rpr = RProgram.circuit_to_rprogram(cr)
                    if test_u:
                        # we measure all the qubits
                        bitstring = rpr.rbits.to01()
                    else:
                        # ... otw only the qubits containing the matrix
                        bitstring = "".join([rpr.rbits[qb.index] for qb in qbit_range])
                else:
                    if test_u:
                        # we measure all the qubits
                        res = self.qpu.submit(cr.to_job())
                    else:
                        # ... otw only the qubits containing the matrix
                        res = self.qpu.submit(cr.to_job(qubits=qbit_range))

                    self.assertEqual(len(res), 1)
                    sample = None
                    for sample in res:
                        pass
                    if sample is None:
                        raise Exception("Unknown flow")
                    bitstring = sample.state.bitstring

                mat_gji = qmatrix.build_matrix_from_bitstring(
                    bitstring, qbit_range, (nrows, ncols)
                )
                mat_gji_diag = mat_gji.diagonal()
                mat_gji_sim = Matrix(matrix_ext).rref(pivots=False) % 2
                mat_gji_sim_diag = mat_gji_sim.diagonal()
                self.logger.debug(f"skip {skip_rightmost}")
                self.logger.debug("original matrix (last column is syndrome)")
                self.logger.debug(f"\n{matrix_ext}")
                self.logger.debug("reduced matrix from qcircuit")
                self.logger.debug(f"\n{mat_gji}")
                if should_iden:
                    self.assertTrue(all(mat_gji_diag))
                    self.assertTrue(all(mat_gji_sim_diag))
                    # check the syndrome calculation is correct
                    syn = mat_gji[:, n].reshape(r, 1)
                    np.testing.assert_array_equal(syn, mat_gji_sim[:, n])
                    if not skip_rightmost:
                        # Additionally, if we didn't skip operations on the
                        # rightmost r*k matrix, the results on this portion
                        # should be equal.
                        np.testing.assert_array_equal(
                            mat_gji[:, r:n], mat_gji_sim[:, r:n]
                        )
                    # # check as well that we can reconstruct the matrix U s.t. U @ matrix = matrix_reduced
                    # if add_qregs and test_u:
                    #     raise Exception("Impossible")
                    #     add_bitstring, swap_bitstring = results.get_qregs_to_bitstring_from_sample(
                    #         [add_qregs, swap_qregs], sample)
                    #     u = rref.build_u_matrix_from_bitstrings(
                    #         swap_bitstring, add_bitstring, r)
                    #     if not skip_rightmost:
                    #         check_matrix = matrix_ext
                    #         check_against = mat_gji
                    #     else:
                    #         # if we skipped the righmost rxn matrix, we should
                    #         # check only the leftmost one AND the syndrome
                    #         range_cols = list(range(r))
                    #         # append syndrome
                    #         range_cols.append(n)
                    #         check_matrix = matrix_ext[:, range_cols]
                    #         check_against = mat_gji[:, range_cols]
                    #     np.testing.assert_array_equal(u @ check_matrix % 2,
                    #                                   check_against)
                else:
                    # in this case, we just check that at least one element on
                    # the diagonal is 0. This is enough to make the algorithm
                    # fail in our isd circuits
                    self.assertFalse(all(mat_gji_diag))
                    self.assertFalse(all(mat_gji_sim_diag))

    @parameterized.expand(
        [
            # ("3x3", np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0]])),
            ("3x3", np.array([[0, 1, 1], [1, 0, 1], [0, 0, 1]])),
            ("3x4", np.array([[1, 1, 0, 0], [1, 0, 0, 0], [0, 1, 1, 1]])),
            ("3x4", np.array([[0, 1, 1, 1], [1, 0, 0, 1], [0, 0, 1, 1]])),
        ]
    )
    def test_iden(self, name, matrix):
        """They should give the same results of a normal GJI and an identity
        matrix on the left."""
        self.logger.debug("test with %s", name)
        self._common_test(matrix, True, True)

    @parameterized.expand(
        [
            ("3x3", np.array([[0, 1, 1], [0, 0, 1], [0, 1, 1]])),
            ("3x4", np.array([[0, 0, 0, 1], [1, 0, 0, 1], [0, 0, 0, 1]])),
            ("3x4", np.array([[1, 1, 1, 0], [1, 1, 1, 0], [1, 0, 0, 0]])),
            ("3x4", np.array([[0, 0, 0, 1], [1, 1, 1, 0], [1, 0, 0, 1]])),
        ]
    )
    def test_no_iden(self, name, matrix):
        self.logger.debug("test with %s", name)
        self._common_test(matrix, True, False)

    @parameterized.expand(
        [
            ("3x5", np.array([[0, 1, 1, 1, 0], [0, 1, 0, 0, 0], [1, 1, 0, 0, 1]])),
            (
                "3x6",
                np.array([[0, 1, 1, 1, 1, 0], [0, 0, 1, 0, 0, 0], [1, 1, 0, 1, 0, 1]]),
            ),
        ]
    )
    @unittest.skipUnless(
        CircuitTestCase.SLOW_TEST_ON or CircuitTestCase.REVERSIBLE_ON,
        CircuitTestCase.SLOW_TEST_ON_REASON,
    )
    def test_iden_slow(self, name, matrix):
        self.logger.debug("test with %s", name)
        self._common_test(matrix, True, True)

    @parameterized.expand(
        [
            ("3x5", np.array([[0, 0, 0, 1, 1], [0, 1, 0, 0, 0], [0, 1, 1, 0, 1]])),
            ("3x5", np.array([[1, 0, 0, 1, 0], [0, 0, 0, 0, 0], [1, 1, 0, 1, 1]])),
        ]
    )
    @unittest.skipUnless(
        CircuitTestCase.SLOW_TEST_ON or CircuitTestCase.REVERSIBLE_ON,
        CircuitTestCase.SLOW_TEST_ON_REASON,
    )
    def test_no_iden_slow(self, name, matrix):
        self.logger.debug("test with %s", name)
        self._common_test(matrix, True, False)
