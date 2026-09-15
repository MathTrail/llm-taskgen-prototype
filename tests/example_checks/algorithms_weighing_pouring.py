"""Answer checks for data/examples/algorithms.weighing_pouring.json: pourings are searched step by step, weighings by trying every plan."""

from collections import deque
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, combinations_with_replacement, product

from example_checks import check

IMPOSSIBLE = "It is impossible"


def only(candidates):
    candidates = list(candidates)
    assert len(candidates) == 1, candidates
    return candidates[0]


def pour_steps(capacities, start, goal, tap=True):
    """Fewest steps from start to a state where goal(state) holds; None if it is never reached."""
    start = tuple(start)
    steps, queue = {start: 0}, deque([start])
    while queue:
        state = queue.popleft()
        if goal(state):
            return steps[state]
        following = []
        for i, capacity in enumerate(capacities):
            if tap:
                following.append(state[:i] + (capacity,) + state[i + 1:])
                following.append(state[:i] + (0,) + state[i + 1:])
            for j in range(len(capacities)):
                if i != j:
                    amount = min(state[i], capacities[j] - state[j])
                    poured = list(state)
                    poured[i] -= amount
                    poured[j] += amount
                    following.append(tuple(poured))
        for nxt in following:
            if nxt not in steps:
                steps[nxt] = steps[state] + 1
                queue.append(nxt)
    return None


def steps_or_impossible(steps):
    return IMPOSSIBLE if steps is None else steps


def one_pan(weights) -> set[int]:
    """Loads that some of the weights balance from the opposite pan."""
    return {sum(chosen) for size in range(1, len(weights) + 1) for chosen in combinations(weights, size)}


def both_pans(weights) -> set[int]:
    """Loads the weights balance when each one is opposite the load, next to it, or unused."""
    return {total for signs in product((1, -1, 0), repeat=len(weights)) if (total := sum(s * w for s, w in zip(signs, weights))) > 0}


def fewest_weights(loads, reach) -> int:
    """Smallest set of whole-kilogram weights whose reach covers every load."""
    loads = set(loads)
    for size in range(1, len(loads) + 1):
        if any(loads <= reach(weights) for weights in combinations_with_replacement(range(1, max(loads) + 1), size)):
            return size
    raise AssertionError("no set of weights works")


@lru_cache(maxsize=None)
def light_weighings(coins: int) -> int:
    """Fewest weighings that always find one lighter coin: k coins go on each pan."""
    if coins <= 1:
        return 0
    return min(1 + max(light_weighings(k), light_weighings(coins - 2 * k)) for k in range(1, coins // 2 + 1))


def fake_weighings(coins: int) -> int:
    """Fewest weighings that always find a fake coin of unknown kind and tell whether it is heavier or lighter.

    A state counts coins that may be heavy or light, only heavy, only light, and surely real.
    """

    def answers(state):
        either, heavy, light, _ = state
        return 2 * either + heavy + light

    @lru_cache(maxsize=None)
    def solvable(state, weighings):
        if answers(state) <= 1:
            return True
        if weighings == 0 or answers(state) > 3**weighings:
            return False
        either, heavy, light, real = state
        for e1, e2, h1, h2, l1, l2 in product(range(either + 1), range(either + 1), range(heavy + 1), range(heavy + 1), range(light + 1), range(light + 1)):
            if e1 + e2 > either or h1 + h2 > heavy or l1 + l2 > light:
                continue
            left, right = e1 + h1 + l1, e2 + h2 + l2
            if left + right == 0 or abs(left - right) > real:  # real coins fill up the lighter-loaded pan
                continue
            balance = (either - e1 - e2, heavy - h1 - h2, light - l1 - l2, real + left + right)
            left_down = (0, e1 + h1, e2 + l2, coins - (e1 + h1 + e2 + l2))
            right_down = (0, e2 + h2, e1 + l1, coins - (e2 + h2 + e1 + l1))
            if all(solvable(outcome, weighings - 1) for outcome in (balance, left_down, right_down)):
                return True
        return False

    return next(weighings for weighings in range(coins + 1) if solvable((coins, 0, 0, 0), weighings))


def split_weighings(total: int, goal: int, limit: int = 6):
    """Fewest weighings to get a pile of goal kg when each weighing halves any group of piles poured together."""
    level = {(Fraction(total),)}
    for weighings in range(limit + 1):
        for piles in level:
            if any(sum(group) == goal for size in range(1, len(piles) + 1) for group in combinations(piles, size)):
                return weighings
        following = set()
        for piles in level:
            for mask in range(1, 2 ** len(piles)):
                chosen = [pile for i, pile in enumerate(piles) if mask >> i & 1]
                rest = [pile for i, pile in enumerate(piles) if not mask >> i & 1]
                half = sum(chosen) / 2
                following.add(tuple(sorted(rest + [half, half])))
        level = following
    return None


@check("wp-34-d1-1")
def w34_d1_1():
    return steps_or_impossible(pour_steps((3, 5), (0, 0), lambda s: 2 in s))


@check("wp-34-d1-2")
def w34_d1_2():
    return only(f"{load} kg" for load in (1, 2, 3, 4) if load not in one_pan((1, 3)))


@check("wp-34-d1-3")
def w34_d1_3():
    return light_weighings(3)


@check("wp-34-d1-4")
def w34_d1_4():
    bucket, jug, capacity = 10, 0, 7
    poured = min(bucket, capacity - jug)
    return bucket - poured


@check("wp-34-d1-5")
def w34_d1_5():
    placements = {  # label: (weights opposite the sugar, weights next to the sugar)
        "Both weights on the pan opposite the sugar": ((1, 2), ()),
        "Both weights on the pan with the sugar": ((), (1, 2)),
        "The 1 kg weight with the sugar, the 2 kg weight opposite": ((2,), (1,)),
        "The 2 kg weight with the sugar, the 1 kg weight opposite": ((1,), (2,)),
    }
    working = [label for label, (opposite, beside) in placements.items() if sum(opposite) - sum(beside) == 3]
    return only(working) if working else "It cannot be done in one weighing"


@check("wp-34-d2-1")
def w34_d2_1():
    return steps_or_impossible(pour_steps((3, 5), (0, 0), lambda s: 4 in s))


@check("wp-34-d2-2")
def w34_d2_2():
    return light_weighings(9)


@check("wp-34-d2-3")
def w34_d2_3():
    return only(f"{load} kg" for load in (2, 5, 7, 10, 11) if load in one_pan((1, 3, 9)))


@check("wp-34-d2-4")
def w34_d2_4():
    return light_weighings(4)


@check("wp-34-d2-5")
def w34_d2_5():
    return steps_or_impossible(pour_steps((5, 2), (0, 0), lambda s: 1 in s))


@check("wp-34-d3-1")
def w34_d3_1():
    return steps_or_impossible(pour_steps((8, 5, 3), (8, 0, 0), lambda s: 4 in s, tap=False))


@check("wp-34-d3-2")
def w34_d3_2():
    return light_weighings(27)


@check("wp-34-d3-3")
def w34_d3_3():
    return only(f"{load} kg" for load in (2, 5, 7, 11, 14) if load not in both_pans((1, 3, 9)))


@check("wp-34-d3-4")
def w34_d3_4():
    return steps_or_impossible(pour_steps((4, 9), (0, 0), lambda s: 6 in s))


@check("wp-34-d3-5")
def w34_d3_5():
    return steps_or_impossible(pour_steps((6, 4), (0, 0), lambda s: 3 in s))


@check("wp-34-d4-1")
def w34_d4_1():
    return light_weighings(12)


@check("wp-34-d4-2")
def w34_d4_2():
    return steps_or_impossible(pour_steps((5, 7), (0, 0), lambda s: 6 in s))


@check("wp-34-d4-3")
def w34_d4_3():
    return fewest_weights(range(1, 8), one_pan)


@check("wp-34-d4-4")
def w34_d4_4():
    return fake_weighings(3)


@check("wp-34-d4-5")
def w34_d4_5():
    def scale(heavy_bag):
        return sum(bag * (11 if bag == heavy_bag else 10) for bag in range(1, 11))

    return only(f"bag {bag}" for bag in range(1, 11) if scale(bag) == 553)


@check("wp-34-d5-1")
def w34_d5_1():
    return fake_weighings(12)


@check("wp-34-d5-2")
def w34_d5_2():
    return steps_or_impossible(pour_steps((8, 5, 3), (8, 0, 0), lambda s: s[0] == 4 and s[1] == 4, tap=False))


@check("wp-34-d5-3")
def w34_d5_3():
    return fewest_weights(range(1, 14), both_pans)


@check("wp-34-d5-4")
def w34_d5_4():
    return light_weighings(10)


@check("wp-34-d5-5")
def w34_d5_5():
    weighings = split_weighings(24, 9)
    return IMPOSSIBLE if weighings is None else weighings
