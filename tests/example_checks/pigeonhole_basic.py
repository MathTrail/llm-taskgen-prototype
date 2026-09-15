"""Answer checks for data/examples/pigeonhole.basic.json: every possible draw or distribution is tried."""

from itertools import combinations, count, product

from example_checks import check

MANY = 20  # "lots of" balls: more than any draw in these tasks needs


def draws(stock: dict[str, int], size: int):
    """Every possible colour count when size items are taken from the stock."""
    names = list(stock)
    for counts in product(*(range(stock[name] + 1) for name in names)):
        if sum(counts) == size:
            yield dict(zip(names, counts))


def sure(stock: dict[str, int], goal) -> int:
    """Smallest number of items that makes goal(counts) true whatever the draw."""
    for size in range(sum(stock.values()) + 1):
        if all(goal(counts) for counts in draws(stock, size)):
            return size
    raise AssertionError("never sure")


def fullest(items: int, boxes: int) -> int:
    """Smallest possible size of the fullest box, trying every way to put the items into the boxes."""
    return min(max(counts) for counts in product(range(items + 1), repeat=boxes) if sum(counts) == items)


def fullest_many(items: int, boxes: int) -> int:
    """The same for numbers too big to try every way: the fullest box is smallest when items are spread evenly."""
    return next(k for k in range(items + 1) if boxes * k >= items)


def pair_same(counts):
    return max(counts.values()) >= 2


def sure_pair_sum(numbers, target: int) -> int:
    """Smallest number of cards that always contains two cards adding up to target."""
    for size in range(1, len(numbers) + 1):
        if all(any(target - x in chosen and target - x != x for x in chosen) for chosen in map(set, combinations(numbers, size))):
            return size
    raise AssertionError("never sure")


@check("pig-12-d1-1")
def p12_d1_1():
    return sure({"red": MANY, "blue": MANY}, pair_same)


@check("pig-12-d1-2")
def p12_d1_2():
    return sure({"red": 3, "green": 3}, lambda c: c["red"] >= 1)


@check("pig-12-d1-3")
def p12_d1_3():
    return fullest(4, 3)


@check("pig-12-d1-4")
def p12_d1_4():
    return sure({"blue": 5, "red": 1}, lambda c: c["red"] >= 1)


@check("pig-12-d1-5")
def p12_d1_5():
    return sure({"green": 4, "yellow": 4}, lambda c: c["yellow"] >= 1)


@check("pig-12-d2-1")
def p12_d2_1():
    return sure({"red": MANY, "blue": MANY, "green": MANY}, pair_same)


@check("pig-12-d2-2")
def p12_d2_2():
    return sure({"red": 4, "blue": 3}, lambda c: c["red"] >= 2)


@check("pig-12-d2-3")
def p12_d2_3():
    return fullest_many(13, 12)


@check("pig-12-d2-4")
def p12_d2_4():
    return sure({"white": 2, "grey": 2, "black": 2}, pair_same)


@check("pig-12-d2-5")
def p12_d2_5():
    return sure({"red": 2, "blue": 3, "green": 4}, lambda c: c["green"] >= 1)


@check("pig-12-d3-1")
def p12_d3_1():
    return sure({"red": 5, "blue": 5, "green": 5}, lambda c: min(c.values()) >= 1)


@check("pig-12-d3-2")
def p12_d3_2():
    return sure({"white": 4, "black": 6}, pair_same)


@check("pig-12-d3-3")
def p12_d3_3():
    return fullest(9, 4)


@check("pig-12-d3-4")
def p12_d3_4():
    return sure({"red": 3, "blue": 3, "green": 3}, lambda c: sum(1 for n in c.values() if n) >= 2)


@check("pig-12-d3-5")
def p12_d3_5():
    return fullest(10, 3)


@check("pig-12-d4-1")
def p12_d4_1():
    return sure({"red": 4, "blue": 5, "green": 6}, lambda c: max(c.values()) >= 3)


@check("pig-12-d4-2")
def p12_d4_2():
    return sure({colour: 2 for colour in range(5)}, pair_same)


@check("pig-12-d4-3")
def p12_d4_3():
    return sure({"red": 6, "blue": 6}, lambda c: min(c.values()) >= 2)


@check("pig-12-d4-4")
def p12_d4_4():
    return sure({"even": 5, "odd": 5}, lambda c: c["even"] >= 1)


@check("pig-12-d4-5")
def p12_d4_5():
    return sure({"red": MANY, "blue": MANY, "green": MANY}, lambda c: max(c.values()) >= 3)


@check("pig-12-d5-1")
def p12_d5_1():
    return sure({"red": 3, "blue": 4, "green": 5}, lambda c: min(c.values()) >= 1)


@check("pig-12-d5-2")
def p12_d5_2():
    stock = {"red left": 3, "red right": 3, "blue left": 3, "blue right": 3}
    return sure(stock, lambda c: (c["red left"] and c["red right"]) or (c["blue left"] and c["blue right"]))


@check("pig-12-d5-3")
def p12_d5_3():
    return sure_pair_sum(range(1, 21), 21)


@check("pig-12-d5-4")
def p12_d5_4():
    return sure({"red": 2, "blue": 2, "green": 2, "yellow": 2}, pair_same)


@check("pig-12-d5-5")
def p12_d5_5():
    fitting = set()
    for red in range(5):
        apples = ["red"] * red + ["green"] * (4 - red)
        if all("red" in three and "green" in three for three in combinations(apples, 3)):
            fitting.add(red)
    assert len(fitting) == 1, fitting
    return fitting.pop()


@check("pig-34-d1-1")
def p34_d1_1():
    return sure({"black": 10, "white": 10}, pair_same)


@check("pig-34-d1-2")
def p34_d1_2():
    return fullest_many(25, 12)


@check("pig-34-d1-3")
def p34_d1_3():
    return sure({"red": 7, "blue": 7}, lambda c: c["red"] >= 2)


@check("pig-34-d1-4")
def p34_d1_4():
    return sure({colour: 10 for colour in ("red", "yellow", "green", "blue")}, pair_same)


@check("pig-34-d1-5")
def p34_d1_5():
    return "Yes, always" if fullest_many(13, 12) >= 2 else "No, never"


@check("pig-34-d2-1")
def p34_d2_1():
    return sure({"red": 5, "blue": 7, "green": 9}, pair_same)


@check("pig-34-d2-2")
def p34_d2_2():
    return fullest_many(37, 7)


@check("pig-34-d2-3")
def p34_d2_3():
    return sure({"red": 10, "blue": 10, "green": 10}, lambda c: c["blue"] >= 1)


@check("pig-34-d2-4")
def p34_d2_4():
    return sure_pair_sum(range(1, 11), 11)


@check("pig-34-d2-5")
def p34_d2_5():
    return fullest_many(30, 4)


@check("pig-34-d3-1")
def p34_d3_1():
    return sure({"red": 4, "blue": 6, "green": 8}, lambda c: max(c.values()) >= 3)


@check("pig-34-d3-2")
def p34_d3_2():
    return sure({"red": 5, "blue": 5, "green": 5}, lambda c: c["red"] >= 2)


@check("pig-34-d3-3")
def p34_d3_3():
    return sure({colour: 2 for colour in range(6)}, lambda c: sum(n // 2 for n in c.values()) >= 2)


@check("pig-34-d3-4")
def p34_d3_4():
    return fullest_many(35, 10)


@check("pig-34-d3-5")
def p34_d3_5():
    return sure({"red": 20, "green": 20, "white": 1}, pair_same)


@check("pig-34-d4-1")
def p34_d4_1():
    return sure({"red": 10, "blue": 10, "green": 10}, lambda c: max(c.values()) >= 10)


@check("pig-34-d4-2")
def p34_d4_2():
    return sure({digit: 2 for digit in range(10)}, pair_same)


@check("pig-34-d4-3")
def p34_d4_3():
    stock = {"red left": 4, "red right": 4, "blue left": 4, "blue right": 4}
    return sure(stock, lambda c: (c["red left"] and c["red right"]) or (c["blue left"] and c["blue right"]))


@check("pig-34-d4-4")
def p34_d4_4():
    return fullest_many(400, 366)


@check("pig-34-d4-5")
def p34_d4_5():
    return sure({"white": 4, "black": 3, "red": 2}, lambda c: min(c.values()) >= 1)


@check("pig-34-d5-1")
def p34_d5_1():
    return sure({"red": 10, "blue": 8, "green": 6, "yellow": 4}, lambda c: max(c.values()) >= 5)


@check("pig-34-d5-2")
def p34_d5_2():
    return next(pupils for pupils in count(1) if fullest_many(pupils, 7) >= 4)


@check("pig-34-d5-3")
def p34_d5_3():
    return next(pupils for pupils in count(1) if fullest_many(pupils, 12) >= 4)


@check("pig-34-d5-4")
def p34_d5_4():
    return sure({colour: 10 for colour in range(4)}, lambda c: sum(n // 2 for n in c.values()) >= 2)


@check("pig-34-d5-5")
def p34_d5_5():
    games = list(combinations(range(6), 2))
    for played in range(2 ** len(games)):
        degrees = [0] * 6
        for index, (a, b) in enumerate(games):
            if played >> index & 1:
                degrees[a] += 1
                degrees[b] += 1
        if len(set(degrees)) == 6:
            return "No, never"
    return "Yes, always"
