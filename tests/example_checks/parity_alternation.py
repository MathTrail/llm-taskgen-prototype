"""Answer checks for data/examples/parity.alternation.json: sequences are simulated and all cases are tried."""

import random
from collections import deque
from itertools import combinations, combinations_with_replacement, permutations, product

from example_checks import check


def only(candidates):
    """The single candidate that passes; fails if none or several pass."""
    candidates = list(candidates)
    assert len(candidates) == 1, candidates
    return candidates[0]


def ordinal(number: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(number, f"{number}th")


def signed_results(last: int) -> set[int]:
    """Every result of 1 +/- 2 +/- ... +/- last."""
    return {
        1 + sum(sign * number for sign, number in zip(signs, range(2, last + 1)))
        for signs in product((1, -1), repeat=last - 1)
    }


def fewest_moves(items: int, per_move: int):
    """Fewest moves, each turning over exactly per_move items, that turn all items over; None if it never happens."""
    start, goal = (1,) * items, (0,) * items
    moves, queue = {start: 0}, deque([start])
    while queue:
        state = queue.popleft()
        if state == goal:
            return moves[state]
        for chosen in combinations(range(items), per_move):
            turned = tuple(side ^ 1 if index in chosen else side for index, side in enumerate(state))
            if turned not in moves:
                moves[turned] = moves[state] + 1
                queue.append(turned)
    return None


def circle_alternates(children: int) -> bool:
    """Whether boys and girls can take turns all the way round a circle of this size."""
    return any(all(row[i] != row[(i + 1) % children] for i in range(children)) for row in product("BG", repeat=children))


@check("par-12-d1-1")
def q12_d1_1():
    return only(n for n in (7, 9, 12, 15, 21) if n % 2 == 0)


@check("par-12-d1-2")
def q12_d1_2():
    return ["red", "blue"][(9 - 1) % 2]


@check("par-12-d1-3")
def q12_d1_3():
    children = 9
    while children >= 2:
        children -= 2
    return children


@check("par-12-d1-4")
def q12_d1_4():
    def on_after(presses):
        on = False
        for _ in range(presses):
            on = not on
        return on

    return only(ordinal(n) for n in (2, 4, 6, 8, 9) if on_after(n))


@check("par-12-d1-5")
def q12_d1_5():
    return list(range(1, 100, 2))[6 - 1]


@check("par-12-d2-1")
def q12_d2_1():
    return len(range(2, 20 + 1, 2))


@check("par-12-d2-2")
def q12_d2_2():
    return (["boy", "girl"] * 5).count("girl")


@check("par-12-d2-3")
def q12_d2_3():
    return only(n for n in (7, 9, 12, 15, 17) if n in range(0, 100, 2))


@check("par-12-d2-4")
def q12_d2_4():
    return only(n for n in (12, 15, 18, 20, 25) if n % 2 == 0 and n % 5 == 0)


@check("par-12-d2-5")
def q12_d2_5():
    return only(n for n in (8, 10, 11, 12, 14) if ["red", "white"][(n - 1) % 2] == "red")


@check("par-12-d3-1")
def q12_d3_1():
    return only(f"{day} March" for day in (2, 10, 15, 20, 28) if day in range(1, 32, 2))


@check("par-12-d3-2")
def q12_d3_2():
    return sum(1 for place in range(1, 16) if ["boy", "girl"][(place - 1) % 2] == "boy")


@check("par-12-d3-3")
def q12_d3_3():
    opened = {number for number in range(1, 21) if number % 2 == 0}
    return sum(1 for number in range(1, 21) if number not in opened)


@check("par-12-d3-4")
def q12_d3_4():
    payable = {2 * coins for coins in range(50)}
    return only(f"{amount} cents" for amount in (7, 11, 15, 16, 19) if amount in payable)


@check("par-12-d3-5")
def q12_d3_5():
    return ["Ann", "Ben", "Kim"][(10 - 1) % 3]


@check("par-12-d4-1")
def q12_d4_1():
    return ["red", "red", "blue"][(20 - 1) % 3]


@check("par-12-d4-2")
def q12_d4_2():
    return sum(1 for number in range(1, 16) if number % 2)


@check("par-12-d4-3")
def q12_d4_3():
    return only(n for n in (7, 9, 11, 12, 13) if circle_alternates(n))


@check("par-12-d4-4")
def q12_d4_4():
    def all_tails_after(moves):
        states = {(1, 1, 1)}
        for _ in range(moves):
            states = {tuple(side ^ (i == coin) for i, side in enumerate(state)) for state in states for coin in range(3)}
        return (0, 0, 0) in states

    return only(n for n in (2, 4, 5, 6, 8) if all_tails_after(n))


@check("par-12-d4-5")
def q12_d4_5():
    sums = {sum(four) for four in combinations_with_replacement(range(1, 26, 2), 4)}
    return only(n for n in (17, 19, 21, 22, 23) if n in sums)


@check("par-12-d5-1")
def q12_d5_1():
    return only(n for n in (0, 2, 4, 5, 10) if n in signed_results(10))


@check("par-12-d5-2")
def q12_d5_2():
    moves = fewest_moves(3, 2)
    return "It can never be done" if moves is None else moves


@check("par-12-d5-3")
def q12_d5_3():
    rng, kinds = random.Random(0), set()
    for _ in range(30):
        board = list(range(1, 21))
        while len(board) > 1:
            a, b = sorted(rng.sample(range(len(board)), 2), reverse=True)
            board.append(board.pop(a) + board.pop(b))
        kinds.add("even" if board[0] % 2 == 0 else "odd")
    return only(kinds)


@check("par-12-d5-4")
def q12_d5_4():
    circle, index = ["Ann", "Ben", "Kim", "Dan", "Eva", "Fay"], 0
    while len(circle) > 1:
        index = (index + 1) % len(circle)  # skip one child, the next steps out
        circle.pop(index)
        index %= len(circle)
    return circle[0]


@check("par-12-d5-5")
def q12_d5_5():
    sheets = [(2 * k - 1, 2 * k) for k in range(1, 26)]
    sums = {sum(front + back for front, back in trio) for trio in combinations(sheets, 3)}
    return only(n for n in (60, 77, 80, 90, 100) if n in sums)


@check("par-34-d1-1")
def q34_d1_1():
    return only(n for n in (6, 10, 13, 20, 28) if (14 + n) % 2 == 1)


@check("par-34-d1-2")
def q34_d1_2():
    return sum(1 for number in range(1, 100) if number % 2)


@check("par-34-d1-3")
def q34_d1_3():
    return ["red", "red", "white"][(50 - 1) % 3]


@check("par-34-d1-4")
def q34_d1_4():
    def kind(a, b):
        odd = (a % 2) + (b % 2)
        return {2: "Both are odd", 0: "Both are even", 1: "One is even and one is odd"}[odd]

    return only({kind(a, b) for a in range(1, 21) for b in range(1, 21) if (a * b) % 2 == 1})


@check("par-34-d1-5")
def q34_d1_5():
    return ["green", "yellow", "red", "yellow"][(30 - 1) % 4]


@check("par-34-d2-1")
def q34_d2_1():
    payable = {7 * price for price in range(1, 100, 2)}
    return only(f"{amount} cents" for amount in (42, 56, 63, 70, 84) if amount in payable)


@check("par-34-d2-2")
def q34_d2_2():
    return sum(range(2, 21, 2)) - sum(range(1, 21, 2))


@check("par-34-d2-3")
def q34_d2_3():
    return "Yes" if circle_alternates(15) else "No"


@check("par-34-d2-4")
def q34_d2_4():
    moves = fewest_moves(7, 2)
    return "It can never be done" if moves is None else moves


@check("par-34-d2-5")
def q34_d2_5():
    return only(n for n in (0, 3, 5, 7, 9) if n in signed_results(11))


@check("par-34-d3-1")
def q34_d3_1():
    sums = {sum(five) for five in combinations_with_replacement(range(1, 50, 2), 5)}
    return only(n for n in (20, 30, 35, 40, 50) if n in sums)


@check("par-34-d3-2")
def q34_d3_2():
    lines = [[("girl", "boy")[(place + start) % 2] for place in range(25)] for start in (0, 1)]
    line = only(line for line in lines if line.count("girl") > line.count("boy"))
    return line.count("girl")


@check("par-34-d3-3")
def q34_d3_3():
    ann = [number for number in range(1, 101) if number % 2]
    return len([number for number in ann if number % 10 != 5])


@check("par-34-d3-4")
def q34_d3_4():
    ends = {sum(jumps) for jumps in product((1, -1), repeat=9)}
    return only(n for n in (0, 2, 4, 7, 10) if n in ends)


@check("par-34-d3-5")
def q34_d3_5():
    on = dict.fromkeys(range(1, 10), False)
    for number in on:
        if number % 2 == 0:
            on[number] = not on[number]
    for number in on:
        if number % 3 == 0:
            on[number] = not on[number]
    return sum(on.values())


@check("par-34-d4-1")
def q34_d4_1():
    def possible(friends):
        if (3 * friends) % 2:
            return False  # hand uses must pair up into whole handshakes
        shakes = {frozenset((i, (i + 1) % friends)) for i in range(friends)}
        shakes |= {frozenset((i, (i + friends // 2) % friends)) for i in range(friends)}
        return all(sum(1 for shake in shakes if i in shake) == 3 for i in range(friends))

    return only(n for n in (5, 7, 8, 9, 11) if possible(n))


@check("par-34-d4-2")
def q34_d4_2():
    return fewest_moves(5, 3)


@check("par-34-d4-3")
def q34_d4_3():
    rng, finals = random.Random(1), set()
    for _ in range(20000):
        board = list(range(1, 21))
        while len(board) > 1:
            a, b = sorted(rng.sample(range(len(board)), 2), reverse=True)
            x, y = board.pop(a), board.pop(b)
            board.append(abs(x - y))
        finals.add(board[0])
        if 2 in finals:
            break
    assert all(final % 2 == 0 for final in finals)
    return only(n for n in (1, 2, 3, 5, 7) if n in finals)


@check("par-34-d4-4")
def q34_d4_4():
    holders, child = [], 1
    while True:
        holders.append(child)
        child = (child - 1 + 4) % 12 + 1
        if child == 1:
            return len(holders)


@check("par-34-d4-5")
def q34_d4_5():
    def splittable(cards):
        total = sum(cards)
        return any(2 * sum(pile) == total for size in range(len(cards) + 1) for pile in combinations(cards, size))

    sets = {f"cards 1 to {last}": range(1, last + 1) for last in (5, 6, 8, 9, 10)}
    return only(name for name, cards in sets.items() if splittable(cards))


@check("par-34-d5-1")
def q34_d5_1():
    return fewest_moves(6, 4)


@check("par-34-d5-2")
def q34_d5_2():
    def possible(pupils):
        if pupils % 2:
            return False  # an odd count of odd numbers is odd, but each friendship is counted twice
        friends = {i: [i ^ 1] for i in range(pupils)}  # pupils 0-1, 2-3, ... are friends in pairs
        return all(len(f) % 2 == 1 for f in friends.values())

    return only(n for n in (21, 23, 25, 26, 27) if possible(n))


@check("par-34-d5-3")
def q34_d5_3():
    return only(n for n in (0, 2, 3, 4, 6) if n in signed_results(9))


@check("par-34-d5-4")
def q34_d5_4():
    results = {sum(d if i % 2 == 0 else -d for i, d in enumerate(order)) for order in permutations(range(1, 7))}
    return only(n for n in (0, 2, 4, 5, 8) if n in results)


@check("par-34-d5-5")
def q34_d5_5():
    rng, breaks = random.Random(2), set()
    for _ in range(200):
        pieces, moves = [(4, 6)], 0
        while any(rows > 1 or cols > 1 for rows, cols in pieces):
            rows, cols = pieces.pop(rng.choice([i for i, (r, c) in enumerate(pieces) if r > 1 or c > 1]))
            if rows > 1 and (cols == 1 or rng.random() < 0.5):
                cut = rng.randint(1, rows - 1)
                pieces += [(cut, cols), (rows - cut, cols)]
            else:
                cut = rng.randint(1, cols - 1)
                pieces += [(rows, cut), (rows, cols - cut)]
            moves += 1
        breaks.add(moves)
    total = only(breaks)
    return "Anya always wins" if total % 2 == 1 else "Borya always wins"
