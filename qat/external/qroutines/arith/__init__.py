from qat.lang.AQASM.gates import AbstractGate
# a_l: int, b_l: int, overflow_qbit, little_endian
adder = AbstractGate("MADD", [int, int, bool, bool])
subtractor = AbstractGate("MSUB", [int, int, bool, bool])
# a_l: int, b_l: int, little_endian
comparator = AbstractGate("MADD", [int, int, bool])
