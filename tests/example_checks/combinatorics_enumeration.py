"""Answer checks for data/examples/combinatorics.enumeration.json: all cases are listed with itertools."""

from itertools import combinations, combinations_with_replacement, permutations, product

from example_checks import check


def coin_ways(amount: int, coins: tuple[int, ...]) -> int:
    """Ways to pay the amount when the order of coins does not matter."""
    return sum(
        1
        for size in range(1, amount + 1)
        for chosen in combinations_with_replacement(coins, size)
        if sum(chosen) == amount
    )


def two_digit(numbers):
    return [n for n in numbers if 10 <= n <= 99]


@check("enum-12-d1-1")
def e12_d1_1():
    return len(list(product(["red", "blue", "yellow"], ["green", "white"])))


@check("enum-12-d1-2")
def e12_d1_2():
    return len(list(combinations(["Ann", "Ben", "Kim"], 2)))


@check("enum-12-d1-3")
def e12_d1_3():
    return len({int(a + b) for a, b in product("12", repeat=2)})


@check("enum-12-d1-4")
def e12_d1_4():
    return sum(1 for line in permutations(["Leo", "Mia", "Zoe"]) if line[0] == "Leo")


@check("enum-12-d1-5")
def e12_d1_5():
    return len(list(product(range(2), range(3))))


@check("enum-12-d2-1")
def e12_d2_1():
    return len(list(combinations(range(4), 2)))


@check("enum-12-d2-2")
def e12_d2_2():
    return len({int(a + b) for a, b in permutations("357", 2)})


@check("enum-12-d2-3")
def e12_d2_3():
    return sum(1 for n in range(1, 31) if "3" in str(n))


@check("enum-12-d2-4")
def e12_d2_4():
    return len(set(permutations(["red", "blue", "green"])))


@check("enum-12-d2-5")
def e12_d2_5():
    return coin_ways(5, (1, 2))


@check("enum-12-d3-1")
def e12_d3_1():
    return len(list(combinations(range(5), 2)))


@check("enum-12-d3-2")
def e12_d3_2():
    return sum(1 for n in range(10, 100) if sum(map(int, str(n))) == 5)


@check("enum-12-d3-3")
def e12_d3_3():
    return len(list(product(range(2), range(3), range(2))))


@check("enum-12-d3-4")
def e12_d3_4():
    coins = (1, 2, 5)
    return len({sum(chosen) for size in range(1, 4) for chosen in combinations(coins, size)})


@check("enum-12-d3-5")
def e12_d3_5():
    return len(set(permutations("RRU")))


@check("enum-12-d4-1")
def e12_d4_1():
    return len({int("".join(p)) for p in permutations("123")})


@check("enum-12-d4-2")
def e12_d4_2():
    return len(list(combinations(range(6), 2)))


@check("enum-12-d4-3")
def e12_d4_3():
    return sum(1 for n in range(10, 100) if len(set(str(n))) == 1)


@check("enum-12-d4-4")
def e12_d4_4():
    return sum(1 for row in permutations(["Ann", "Ben", "Kim"]) if abs(row.index("Ann") - row.index("Ben")) != 1)


@check("enum-12-d4-5")
def e12_d4_5():
    return len(list(product("HT", repeat=3)))


@check("enum-12-d5-1")
def e12_d5_1():
    return sum(1 for n in range(10, 100) if sum(map(int, str(n))) == 10)


@check("enum-12-d5-2")
def e12_d5_2():
    shirts, trousers = ["red", "white", "blue"], ["green", "black", "grey"]
    return sum(1 for s, t in product(shirts, trousers) if (s, t) != ("red", "green"))


@check("enum-12-d5-3")
def e12_d5_3():
    via_birch = list(product(["r1", "r2", "r3"], ["s1", "s2"]))
    straight = [("direct",)]
    return len(via_birch) + len(straight)


@check("enum-12-d5-4")
def e12_d5_4():
    return sum(1 for line in permutations(["Tom", "c1", "c2", "c3"]) if line.index("Tom") in (0, 3))


@check("enum-12-d5-5")
def e12_d5_5():
    return len(two_digit({int(a + b) for a, b in product("012", repeat=2)}))


@check("enum-34-d1-1")
def e34_d1_1():
    return len(list(combinations(range(6), 2)))


@check("enum-34-d1-2")
def e34_d1_2():
    return len(list(product(range(4), range(3))))


@check("enum-34-d1-3")
def e34_d1_3():
    return len({int("".join(p)) for p in permutations("4567", 3)})


@check("enum-34-d1-4")
def e34_d1_4():
    return len(list(permutations(range(5), 2)))  # ordered pairs: home team, away team


@check("enum-34-d1-5")
def e34_d1_5():
    return sum(1 for n in range(10, 100) if "5" in str(n))


@check("enum-34-d2-1")
def e34_d2_1():
    return len(list(combinations(range(5), 2)))


@check("enum-34-d2-2")
def e34_d2_2():
    return coin_ways(7, (1, 2, 5))


@check("enum-34-d2-3")
def e34_d2_3():
    return len({int("".join(p)) for p in product("123", repeat=3)})


@check("enum-34-d2-4")
def e34_d2_4():
    return len(list(permutations(range(7), 2)))  # sender, receiver


@check("enum-34-d2-5")
def e34_d2_5():
    return len(list(product("XYZ", "1234")))


@check("enum-34-d3-1")
def e34_d3_1():
    return sum(1 for n in range(10, 100) if n // 10 > n % 10)


@check("enum-34-d3-2")
def e34_d3_2():
    return len(list(combinations(range(6), 2))) + 1


@check("enum-34-d3-3")
def e34_d3_3():
    return sum(1 for shelf in permutations(["red", "b2", "b3", "b4"]) if shelf[0] == "red")


@check("enum-34-d3-4")
def e34_d3_4():
    return sum(1 for n in range(100, 1000) if sum(map(int, str(n))) == 3)


@check("enum-34-d3-5")
def e34_d3_5():
    children = ["b1", "b2", "b3", "g1", "g2", "g3", "g4"]
    return sum(1 for pair in combinations(children, 2) if not all(c.startswith("g") for c in pair))


@check("enum-34-d4-1")
def e34_d4_1():
    return sum(1 for n in range(1, 101) if "7" in str(n))


@check("enum-34-d4-2")
def e34_d4_2():
    return len(list(combinations("1234", 3)))  # combinations come out in increasing order


@check("enum-34-d4-3")
def e34_d4_3():
    return len(set(permutations("RRRUU")))


@check("enum-34-d4-4")
def e34_d4_4():
    stickers = range(5)
    return sum(
        1
        for dasha in combinations(stickers, 2)
        for pasha in stickers
        if pasha not in dasha
    )


@check("enum-34-d4-5")
def e34_d4_5():
    return sum(str(n).count("1") for n in range(1, 31))


@check("enum-34-d5-1")
def e34_d5_1():
    return sum(1 for n in range(100, 1000) if sum(map(int, str(n))) == 5)


@check("enum-34-d5-2")
def e34_d5_2():
    return sum(1 for team in combinations(range(7), 3) for captain in team)


@check("enum-34-d5-3")
def e34_d5_3():
    return coin_ways(20, (2, 5, 10))


@check("enum-34-d5-4")
def e34_d5_4():
    return next(n for n in range(2, 100) if len(list(combinations(range(n), 2))) == 28)


@check("enum-34-d5-5")
def e34_d5_5():
    return len({int("".join(p)) for p in permutations("0123") if p[0] != "0"})
