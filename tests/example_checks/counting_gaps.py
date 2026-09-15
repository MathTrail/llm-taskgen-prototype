"""Answer checks for data/examples/counting.gaps.json: gaps, posts, cuts, floors, pages and places in a line."""

from itertools import pairwise

from example_checks import check


def gaps(objects: int) -> int:
    """Gaps between neighbours in a row, counted pair by pair."""
    return len(list(pairwise(range(objects))))


def ring_gaps(objects: int) -> int:
    """Gaps between neighbours in a closed ring, where the last object is next to the first."""
    return len({frozenset((i, (i + 1) % objects)) for i in range(objects)})


def cuts_for(pieces: int) -> int:
    """Cuts needed to get the pieces, one cut at a time."""
    count, cuts = 1, 0
    while count < pieces:
        cuts += 1
        count += 1
    return cuts


def flights(start: int, end: int) -> int:
    """Flights of stairs walked from floor start up to floor end."""
    return len(list(pairwise(range(start, end + 1))))


def line_length(place_from_front: int, place_from_back: int) -> int:
    """Length of the only line in which one person has both places."""
    return next(n for n in range(1, 500) if n - place_from_front + 1 == place_from_back)


@check("gaps-12-d1-1")
def g12_d1_1():
    return gaps(6)


@check("gaps-12-d1-2")
def g12_d1_2():
    return cuts_for(4)


@check("gaps-12-d1-3")
def g12_d1_3():
    return next(flowers for flowers in range(1, 50) if gaps(flowers) == 4)


@check("gaps-12-d1-4")
def g12_d1_4():
    return len(range(3, 7 + 1))


@check("gaps-12-d1-5")
def g12_d1_5():
    return flights(1, 4)


@check("gaps-12-d2-1")
def g12_d2_1():
    posts = [2 * i for i in range(8)]
    return posts[-1] - posts[0]


@check("gaps-12-d2-2")
def g12_d2_2():
    return cuts_for(5) * 3


@check("gaps-12-d2-3")
def g12_d2_3():
    return line_length(3, 3)


@check("gaps-12-d2-4")
def g12_d2_4():
    return flights(1, 3) * 10


@check("gaps-12-d2-5")
def g12_d2_5():
    return len(range(10, 20 + 1))


@check("gaps-12-d3-1")
def g12_d3_1():
    return 2 * gaps(6)


@check("gaps-12-d3-2")
def g12_d3_2():
    return ring_gaps(8)


@check("gaps-12-d3-3")
def g12_d3_3():
    line = ["front"] * 3 + ["Kate"] + ["back"] * 3
    assert line.index("Kate") + 1 == 4
    return len(line)


@check("gaps-12-d3-4")
def g12_d3_4():
    return flights(1, 4) * 8


@check("gaps-12-d3-5")
def g12_d3_5():
    string = "R" + "BBR" * gaps(5)
    assert string.count("R") == 5
    return string.count("B")


@check("gaps-12-d4-1")
def g12_d4_1():
    per_cut = 6 // cuts_for(3)
    return cuts_for(6) * per_cut


@check("gaps-12-d4-2")
def g12_d4_2():
    per_flight = 20 // flights(1, 3)
    return flights(1, 5) * per_flight


@check("gaps-12-d4-3")
def g12_d4_3():
    return line_length(5, 7)


@check("gaps-12-d4-4")
def g12_d4_4():
    side = range(3)
    return len({(x, y) for x in side for y in side if x in (0, 2) or y in (0, 2)})


@check("gaps-12-d4-5")
def g12_d4_5():
    return flights(3, 10)


@check("gaps-12-d5-1")
def g12_d5_1():
    return 3 * cuts_for(4) * 2


@check("gaps-12-d5-2")
def g12_d5_2():
    return len(range(7 + 1, 14))


@check("gaps-12-d5-3")
def g12_d5_3():
    landings = list(range(1, 9 + 1, 2))
    assert landings[-1] == 9
    return len(landings) - 1


@check("gaps-12-d5-4")
def g12_d5_4():
    return len(range(0, 20 + 1, 2))


@check("gaps-12-d5-5")
def g12_d5_5():
    per_flight = 20 // flights(1, 3)
    return flights(1, 6) * per_flight


@check("gaps-34-d1-1")
def g34_d1_1():
    trees = [5 * i for i in range(21)]
    return trees[-1] - trees[0]


@check("gaps-34-d1-2")
def g34_d1_2():
    return len(range(2, 12, 2))


@check("gaps-34-d1-3")
def g34_d1_3():
    return len(range(25, 60 + 1))


@check("gaps-34-d1-4")
def g34_d1_4():
    return flights(1, 9) * 18


@check("gaps-34-d1-5")
def g34_d1_5():
    return ring_gaps(24)


@check("gaps-34-d2-1")
def g34_d2_1():
    return cuts_for(7) * 4


@check("gaps-34-d2-2")
def g34_d2_2():
    per_gap = 6 // gaps(3)
    return gaps(7) * per_gap


@check("gaps-34-d2-3")
def g34_d2_3():
    return line_length(12, 15)


@check("gaps-34-d2-4")
def g34_d2_4():
    return len(range(0, 60 + 1, 4))


@check("gaps-34-d2-5")
def g34_d2_5():
    return sum(len(str(page)) for page in range(1, 25 + 1))


@check("gaps-34-d3-1")
def g34_d3_1():
    per_flight = 30 // flights(1, 4)
    return flights(1, 10) * per_flight


@check("gaps-34-d3-2")
def g34_d3_2():
    return ring_gaps(15) * 2


@check("gaps-34-d3-3")
def g34_d3_3():
    line = ["x"] * 6 + ["Masha"] + ["y"] * 3 + ["Dasha"] + ["z"] * 4
    assert line.index("Masha") + 1 == 7
    assert len(line) - line.index("Dasha") == 5
    return len(line)


@check("gaps-34-d3-4")
def g34_d3_4():
    cut_marks = range(10, 100, 10)
    return len(cut_marks) * 3


@check("gaps-34-d3-5")
def g34_d3_5():
    return len(range(3, 21 + 1, 2))


@check("gaps-34-d4-1")
def g34_d4_1():
    per_cut = 12 // cuts_for(4)
    return cuts_for(7) * per_cut


@check("gaps-34-d4-2")
def g34_d4_2():
    return next(n for n in range(1, 200) if sum(len(str(page)) for page in range(1, n + 1)) == 39)


@check("gaps-34-d4-3")
def g34_d4_3():
    return 2 * len(range(0, 90 + 1, 10))


@check("gaps-34-d4-4")
def g34_d4_4():
    per_flight = 36 // flights(1, 3)
    return flights(3, 7) * per_flight


@check("gaps-34-d4-5")
def g34_d4_5():
    lamps = {30 * i for i in range(11)} | {30 * i + 15 for i in range(10)}
    return len(lamps)


@check("gaps-34-d5-1")
def g34_d5_1():
    cuts, minutes = cuts_for(6), 0
    for cut in range(1, cuts + 1):
        minutes += 5
        if cut < cuts:
            minutes += 2
    return minutes


@check("gaps-34-d5-2")
def g34_d5_2():
    coloured = list(range(3, 50 + 1, 3))
    return sum(1 for cell in range(coloured[0], coloured[-1] + 1) if cell not in coloured)


@check("gaps-34-d5-3")
def g34_d5_3():
    marks = range(0, 20 + 1, 4)
    return len({(x, y) for x in marks for y in marks if x in (0, 20) or y in (0, 20)})


@check("gaps-34-d5-4")
def g34_d5_4():
    per_flight = 60 // flights(1, 5)
    return flights(3, 9) * per_flight


@check("gaps-34-d5-5")
def g34_d5_5():
    tables, seats = 8, 0
    for i in range(tables):
        seats += 2  # front and back
        seats += (i == 0) + (i == tables - 1)  # the free ends of the row
    return seats
