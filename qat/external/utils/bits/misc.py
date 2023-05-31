import logging

LOGGER = logging.getLogger(__name__)


def assert_enough_bits(
    a_int: int, bits: int, signed=False, ones_complement=False, twos_complement=True
):
    bits_required = get_required_bits(a_int, signed, ones_complement, twos_complement)
    assert bits >= bits_required, "Not enough bits."


def get_required_bits(
    *ints: int, signed=False, ones_complement=False, twos_complement=True
) -> int:
    """Get the minimum number of bits required to represent all the integers.

    Said differently, it returns the log2 of the biggest positive /
    smallest negative integer. The number of bits required depends on
    the enabled flags.
    """
    if len(ints) == 0:
        raise ValueError("number of ints must be greater than 0")
    if len(ints) == 1:
        to_check_int = ints[0]
    elif not signed:
        if any(i < 0 for i in ints):
            raise ValueError("signed flag on, all ints must be non-negative")
        to_check_int = max(ints)
    elif ones_complement:
        maxi = abs(max(ints))
        mini = abs(min(ints))
        to_check_int = max(maxi, mini)
    elif twos_complement:
        maxi = abs(max(ints))
        mini = ~min(ints)
        to_check_int = max(maxi, mini)
    # bits_required = ceil(log(to_check_int, 2))
    bits_required = len("{:b}".format(to_check_int))
    if signed:
        bits_required += 1
    return bits_required
