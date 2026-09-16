"""Answer checks for data/examples/arithmetic.tricks.json: sums are computed directly and thought-of numbers are searched for."""

from fractions import Fraction
from math import prod

from example_checks import check


def thought(rule) -> int:
    """The only whole number from 0 to 1000 that fits the rule; fails if none or several fit."""
    fitting = [n for n in range(1001) if rule(Fraction(n))]
    assert len(fitting) == 1, fitting
    return fitting[0]


def trailing_zeros(number: int) -> int:
    text = str(number)
    return len(text) - len(text.rstrip("0"))


@check("tri-12-d1-1")
def t12_d1_1():
    return sum(range(1, 10))


@check("tri-12-d1-2")
def t12_d1_2():
    return thought(lambda n: n + 5 == 12)


@check("tri-12-d1-3")
def t12_d1_3():
    return 38 + 27 + 2


@check("tri-12-d1-4")
def t12_d1_4():
    return thought(lambda n: n - 4 == 6)


@check("tri-12-d1-5")
def t12_d1_5():
    return 9 + 9 + 9 + 1 + 1 + 1


@check("tri-12-d2-1")
def t12_d2_1():
    return 25 + 36 + 75


@check("tri-12-d2-2")
def t12_d2_2():
    return thought(lambda n: n + 3 + 3 == 15)


@check("tri-12-d2-3")
def t12_d2_3():
    return 10 - 9 + 8 - 7 + 6 - 5 + 4 - 3 + 2 - 1


@check("tri-12-d2-4")
def t12_d2_4():
    return 5 * 10 - 5


@check("tri-12-d2-5")
def t12_d2_5():
    return thought(lambda n: n + 7 - 7 == 12)


@check("tri-12-d3-1")
def t12_d3_1():
    return sum(range(11, 20))


@check("tri-12-d3-2")
def t12_d3_2():
    return thought(lambda n: n + 8 - 3 == 20)


@check("tri-12-d3-3")
def t12_d3_3():
    return 99 + 98 + 2 + 1


@check("tri-12-d3-4")
def t12_d3_4():
    return thought(lambda n: n + n == 18)


@check("tri-12-d3-5")
def t12_d3_5():
    return 37 + 45 + 63 + 55


@check("tri-12-d4-1")
def t12_d4_1():
    return thought(lambda n: 2 * n + 4 == 20)


@check("tri-12-d4-2")
def t12_d4_2():
    return sum(range(1, 11)) + sum(range(1, 10))


@check("tri-12-d4-3")
def t12_d4_3():
    return 2 * 7 * 5


@check("tri-12-d4-4")
def t12_d4_4():
    return thought(lambda n: n + 6 - 10 == 5)


@check("tri-12-d4-5")
def t12_d4_5():
    return 50 - sum(range(1, 10))


@check("tri-12-d5-1")
def t12_d5_1():
    return sum(range(1, 21))


@check("tri-12-d5-2")
def t12_d5_2():
    return thought(lambda n: n + 5 == 2 * n)


@check("tri-12-d5-3")
def t12_d5_3():
    return sum(11 * digit for digit in range(1, 10))


@check("tri-12-d5-4")
def t12_d5_4():
    # "Half of them" needs a whole number of sweets in each half.
    return thought(lambda n: n % 2 == 0 and n - n / 2 - 1 == 4)


@check("tri-12-d5-5")
def t12_d5_5():
    return sum(n if n % 2 == 0 else -n for n in range(100, 0, -1))


@check("tri-34-d1-1")
def t34_d1_1():
    return 25 * 7 * 4


@check("tri-34-d1-2")
def t34_d1_2():
    return thought(lambda n: 3 * n == 27)


@check("tri-34-d1-3")
def t34_d1_3():
    return 48 + 76 + 52 + 24


@check("tri-34-d1-4")
def t34_d1_4():
    return 999 + 99 + 9 + 3


@check("tri-34-d1-5")
def t34_d1_5():
    return 5 * 17 * 2


@check("tri-34-d2-1")
def t34_d2_1():
    return sum(range(1, 20, 2))


@check("tri-34-d2-2")
def t34_d2_2():
    return thought(lambda n: n / 4 + 6 == 11)


@check("tri-34-d2-3")
def t34_d2_3():
    return 4 * 13 * 25


@check("tri-34-d2-4")
def t34_d2_4():
    return sum(range(36, 45))


@check("tri-34-d2-5")
def t34_d2_5():
    return 17 * 4 + 17 * 6


@check("tri-34-d3-1")
def t34_d3_1():
    return thought(lambda n: 5 * n - 7 == 23)


@check("tri-34-d3-2")
def t34_d3_2():
    return sum(range(1, 31))


@check("tri-34-d3-3")
def t34_d3_3():
    return 999 * 5 + 5


@check("tri-34-d3-4")
def t34_d3_4():
    return thought(lambda n: n + 12 == 3 * n)


@check("tri-34-d3-5")
def t34_d3_5():
    return 1 + 2 - 3 + 4 + 5 - 6 + 7 + 8 - 9 + 10 + 11 - 12


@check("tri-34-d4-1")
def t34_d4_1():
    return 25 * 32


@check("tri-34-d4-2")
def t34_d4_2():
    return thought(lambda n: (n + 7) * 2 == 30)


@check("tri-34-d4-3")
def t34_d4_3():
    return 101 * 23


@check("tri-34-d4-4")
def t34_d4_4():
    return sum(range(2, 41, 2))


@check("tri-34-d4-5")
def t34_d4_5():
    return thought(lambda n: 50 - n == n + 14)


@check("tri-34-d5-1")
def t34_d5_1():
    return sum(range(1, 100, 2)) - sum(range(2, 99, 2))


@check("tri-34-d5-2")
def t34_d5_2():
    return thought(lambda n: ((n + 3) * 3 - 3) / 3 == 8)


@check("tri-34-d5-3")
def t34_d5_3():
    runs = [range(start, start + 5) for start in range(100) if sum(range(start, start + 5)) == 100]
    assert len(runs) == 1, runs
    return max(runs[0])


@check("tri-34-d5-4")
def t34_d5_4():
    return trailing_zeros(prod(range(1, 16)))


@check("tri-34-d5-5")
def t34_d5_5():
    quotient = Fraction(2 * 4 * 6 * 8 * 10, 1 * 2 * 3 * 4 * 5)
    assert quotient.denominator == 1
    return int(quotient)
