"""Answer checks for data/examples/logic.ordering.json: every order of the people or things is tried."""

from itertools import permutations

from example_checks import check


def orders(items, *rules):
    """All orders of items (index 0 = tallest, oldest, first in line, leftmost...) in which every rule holds.

    A rule gets a dict item -> place, counted from 1.
    """
    found = []
    for order in permutations(items):
        place = {item: index + 1 for index, item in enumerate(order)}
        if all(rule(place) for rule in rules):
            found.append(order)
    assert found, "no order fits the rules"
    return found


def unique(values):
    """The single value that all fitting orders agree on."""
    values = set(values)
    assert len(values) == 1, values
    return values.pop()


def ordinal(number: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(number, f"{number}th")


@check("ord-12-d1-1")
def o12_d1_1():
    found = orders(["Ann", "Ben", "Kim"], lambda p: p["Ann"] < p["Ben"], lambda p: p["Ben"] < p["Kim"])
    return unique(order[-1] for order in found)


@check("ord-12-d1-2")
def o12_d1_2():
    found = orders(
        ["the hare", "the fox", "the mouse"],
        lambda p: p["the hare"] < p["the fox"],
        lambda p: p["the fox"] < p["the mouse"],
    )
    return unique(order[-1] for order in found)


@check("ord-12-d1-3")
def o12_d1_3():
    found = orders(["Tom", "Sam", "Leo"], lambda p: p["Tom"] < p["Sam"], lambda p: p["Sam"] < p["Leo"])
    return unique(len(order) - order.index("Tom") - 1 for order in found)


@check("ord-12-d1-4")
def o12_d1_4():
    found = orders(["Mia", "Zoe", "Lily"], lambda p: p["Mia"] < p["Zoe"], lambda p: p["Lily"] < p["Mia"])
    return unique(order[0] for order in found)


@check("ord-12-d1-5")
def o12_d1_5():
    found = orders(
        ["the red box", "the blue box", "the green box"],
        lambda p: p["the red box"] < p["the blue box"],
        lambda p: p["the blue box"] < p["the green box"],
    )
    return unique(order[-1] for order in found)


@check("ord-12-d2-1")
def o12_d2_1():
    found = orders(
        ["Ann", "Ben", "Kim", "Dan"],
        lambda p: p["Kim"] == 1,
        lambda p: p["Dan"] == 4,
        lambda p: p["Ann"] == p["Ben"] + 1,
    )
    return unique(order[1] for order in found)


@check("ord-12-d2-2")
def o12_d2_2():
    found = orders(["Leo", "f1", "f2", "f3", "f4"], lambda p: p["Leo"] == 3)
    return unique(len(order) - order.index("Leo") - 1 for order in found)


@check("ord-12-d2-3")
def o12_d2_3():
    found = orders(
        ["Rex", "Spot", "Max", "Bo"],
        lambda p: p["Rex"] < p["Spot"],
        lambda p: p["Spot"] < p["Max"],
        lambda p: p["Max"] < p["Bo"],
    )
    return unique(order[1] for order in found)


@check("ord-12-d2-4")
def o12_d2_4():
    found = orders(
        ["Eva", "Tom", "Max", "Leo"],
        lambda p: p["Eva"] < p["Tom"],
        lambda p: p["Tom"] < p["Max"],
        lambda p: p["Max"] < p["Leo"],
    )
    return unique(order[2] for order in found)


@check("ord-12-d2-5")
def o12_d2_5():
    found = orders(
        ["Grandma", "Mum", "Kate", "Dad"],
        lambda p: p["Grandma"] < p["Mum"],
        lambda p: p["Mum"] < p["Kate"],
        lambda p: p["Dad"] < p["Mum"],
        lambda p: p["Grandma"] < p["Dad"],
    )
    return unique(order.index("Kate") for order in found)


@check("ord-12-d3-1")
def o12_d3_1():
    found = orders(
        ["Ann", "Kim", "Ben", "Dan", "Eva"],
        lambda p: p["Ann"] == 1,
        lambda p: p["Kim"] == p["Ann"] + 1,
        lambda p: p["Ben"] == p["Kim"] + 1,
        lambda p: p["Dan"] == 5,
    )
    return unique(ordinal(order.index("Eva") + 1) for order in found)


@check("ord-12-d3-2")
def o12_d3_2():
    found = orders(
        ["Tom", "Sam", "Leo", "Max"],
        lambda p: p["Tom"] < p["Sam"],
        lambda p: p["Leo"] < p["Tom"],
        lambda p: p["Sam"] < p["Max"],
    )
    return unique(order[1] for order in found)


@check("ord-12-d3-3")
def o12_d3_3():
    found = orders(
        ["Nina", "Olga", "Pete", "Rita"],
        lambda p: p["Nina"] not in (1, 4),
        lambda p: p["Olga"] == p["Nina"] - 1,
        lambda p: p["Pete"] > p["Nina"],
        lambda p: p["Rita"] == 4,
    )
    return unique(order[0] for order in found)


@check("ord-12-d3-4")
def o12_d3_4():
    found = orders(
        ["the red book", "the blue book", "the green book", "the yellow book"],
        lambda p: p["the red book"] < p["the blue book"],
        lambda p: p["the green book"] > p["the blue book"],
        lambda p: p["the yellow book"] < p["the red book"],
    )
    return unique(order[-1] for order in found)


@check("ord-12-d3-5")
def o12_d3_5():
    found = orders(
        ["Leo", "Max", "Sam", "Tom"],
        lambda p: p["Leo"] < p["Max"],
        lambda p: p["Sam"] < p["Leo"],
        lambda p: p["Tom"] < p["Sam"],
    )
    return unique(order.index("Max") for order in found)


@check("ord-12-d4-1")
def o12_d4_1():
    found = orders(
        ["Ann", "Bea", "Cleo", "Dora", "Emma"],
        lambda p: p["Ann"] < p["Bea"],
        lambda p: p["Cleo"] < p["Ann"],
        lambda p: p["Dora"] == p["Bea"] + 1,
        lambda p: p["Emma"] == 5,
    )
    return unique(order[1] for order in found)


@check("ord-12-d4-2")
def o12_d4_2():
    found = orders(
        ["Kim", "Lily", "Mia", "Nora"],
        lambda p: p["Nora"] == 1,
        lambda p: p["Kim"] < p["Lily"],
        lambda p: p["Kim"] < p["Mia"],
        lambda p: p["Lily"] != 4,
    )
    return unique(order[-1] for order in found)


@check("ord-12-d4-3")
def o12_d4_3():
    found = orders(["Tom", "Sam", "c1", "c2", "c3"], lambda p: p["Sam"] - p["Tom"] == 3)
    return len({order.index("Tom") + 1 for order in found})


@check("ord-12-d4-4")
def o12_d4_4():
    found = orders(
        ["the jam", "the honey", "the salt", "the pickles"],
        lambda p: p["the salt"] == 1,
        lambda p: p["the honey"] not in (1, 4),
        lambda p: p["the jam"] == p["the honey"] + 1,
        lambda p: abs(p["the pickles"] - p["the salt"]) != 1,
    )
    return unique(order[-1] for order in found)


@check("ord-12-d4-5")
def o12_d4_5():
    winners = set()
    for ben in range(50):
        stamps = {"Ann": ben + 2, "Ben": ben, "Kim": ben + 3}
        winners.add(max(stamps, key=stamps.get))
    return unique(winners)


@check("ord-12-d5-1")
def o12_d5_1():
    found = orders(
        ["Ann", "Ben", "Kim", "Dan", "Eva"],
        lambda p: p["Kim"] == 5,
        lambda p: p["Dan"] == 4,
        lambda p: p["Ann"] not in (1, 5),
        lambda p: p["Ben"] == p["Ann"] - 1,
        lambda p: p["Eva"] != 1,
    )
    return unique(ordinal(order.index("Eva") + 1) for order in found)


@check("ord-12-d5-2")
def o12_d5_2():
    found = orders(
        ["Leo", "Max", "Nick", "Oleg"],
        lambda p: p["Leo"] < p["Max"],
        lambda p: p["Oleg"] < p["Nick"],
        lambda p: p["Max"] < p["Oleg"],
    )
    return unique(order[-1] for order in found)


@check("ord-12-d5-3")
def o12_d5_3():
    red, blue, green, yellow, white = "the red house", "the blue house", "the green house", "the yellow house", "the white house"
    found = orders(
        [red, blue, green, yellow, white],
        lambda p: p[yellow] == 1,
        lambda p: abs(p[white] - p[yellow]) == 1,
        lambda p: abs(p[red] - p[white]) == 1,
        lambda p: abs(p[green] - p[red]) == 1,
        lambda p: abs(p[green] - p[blue]) == 1,
    )
    return unique(order[-1] for order in found)


@check("ord-12-d5-4")
def o12_d5_4():
    found = orders(
        ["Sam", "Tom", "Ula", "Vera"],
        lambda p: p["Sam"] in (1, 4),
        lambda p: abs(p["Tom"] - p["Sam"]) == 1,
        lambda p: abs(p["Vera"] - p["Tom"]) != 1,
    )
    return unique(order[-1] if order[0] == "Sam" else order[0] for order in found)


@check("ord-12-d5-5")
def o12_d5_5():
    youngest = set()
    for ben in range(5, 50):
        ages = {"Ben": ben, "Ann": ben + 2, "Kim": ben + 3}
        ages["Dan"] = ages["Kim"] - 1
        low = min(ages.values())
        assert list(ages.values()).count(low) == 1
        youngest.add(min(ages, key=ages.get))
    return unique(youngest)


@check("ord-34-d1-1")
def o34_d1_1():
    names = ["Ann", "Ben", "Kim", "Dan", "Eva"]
    found = orders(names, *[lambda p, a=a, b=b: p[a] < p[b] for a, b in zip(names, names[1:])])
    return unique(order[2] for order in found)


@check("ord-34-d1-2")
def o34_d1_2():
    return unique(ordinal(place) for place in range(1, 30) if place + 3 == 7)


@check("ord-34-d1-3")
def o34_d1_3():
    boxes = ["red", "green", "blue", "box4", "box5"]
    weights = set()
    for masses in permutations(range(1, 6)):
        mass = dict(zip(boxes, masses))
        if mass["green"] == 3 and mass["green"] < mass["red"] < mass["blue"]:
            weights.add(mass["red"])
    return unique(weights)


@check("ord-34-d1-4")
def o34_d1_4():
    found = orders(["Nina", "c1", "c2", "c3", "c4", "c5", "c6"], lambda p: p["Nina"] == 5)
    return unique(order.index("Nina") for order in found)


@check("ord-34-d1-5")
def o34_d1_5():
    found = orders(
        ["Tom", "Sam", "Leo", "Max"],
        lambda p: p["Tom"] < p["Sam"],
        lambda p: p["Sam"] < p["Leo"],
        lambda p: p["Max"] < p["Tom"],
    )
    return unique(order[-1] for order in found)


@check("ord-34-d2-1")
def o34_d2_1():
    found = orders(
        ["Oak", "Pine", "Reed", "Stone"],
        lambda p: min(p["Oak"], p["Reed"]) < p["Pine"] < max(p["Oak"], p["Reed"]),
        lambda p: p["Stone"] in (1, 4),
        lambda p: abs(p["Stone"] - p["Reed"]) == 1,
    )
    return unique(order[-1] if order[0] == "Stone" else order[0] for order in found)


@check("ord-34-d2-2")
def o34_d2_2():
    found = orders(
        ["Dan", "Eva", "Fay", "Gil", "Hal"],
        lambda p: p["Hal"] == 1,
        lambda p: p["Eva"] < p["Dan"] < p["Fay"],
        lambda p: p["Gil"] == p["Fay"] + 1,
    )
    return unique(order[2] for order in found)


@check("ord-34-d2-3")
def o34_d2_3():
    found = orders(
        ["red", "blue", "green", "white"],
        lambda p: p["red"] < p["blue"],
        lambda p: p["blue"] < p["green"],
        lambda p: p["white"] < p["red"],
    )
    return unique(len(order) - order.index("red") - 1 for order in found)


@check("ord-34-d2-4")
def o34_d2_4():
    found = orders(
        ["Oleg", "Petr", "Rita", "Sasha", "Tanya"],
        lambda p: p["Oleg"] < p["Petr"],
        lambda p: p["Rita"] < p["Oleg"],
        lambda p: p["Petr"] < p["Sasha"],
        lambda p: p["Tanya"] < p["Rita"],
    )
    return unique(order[-1] for order in found)


@check("ord-34-d2-5")
def o34_d2_5():
    found = orders(
        ["Kim", "Lea", "Mo"],
        lambda p: p["Mo"] != 2,
        lambda p: p["Lea"] == p["Mo"] + 1,
        lambda p: p["Kim"] != 1,
    )
    return unique(order[1] for order in found)


@check("ord-34-d3-1")
def o34_d3_1():
    found = orders(
        ["Dan", "Eva", "Fay", "Ann", "Ben", "Kim"],
        lambda p: p["Dan"] == 1,
        lambda p: p["Eva"] == 6,
        lambda p: p["Fay"] == 2,
        lambda p: p["Ann"] == p["Ben"] + 1,
        lambda p: p["Kim"] == p["Ann"] + 1,
    )
    return unique(order[4] for order in found)


@check("ord-34-d3-2")
def o34_d3_2():
    found = orders(
        ["Anna", "Boris", "Vera", "Gleb"],
        lambda p: p["Anna"] < p["Boris"],
        lambda p: p["Gleb"] < p["Vera"],
        lambda p: p["Boris"] < p["Gleb"],
    )
    return unique(order[2] for order in found)


@check("ord-34-d3-3")
def o34_d3_3():
    places = set()
    for blue in range(1, 20):
        red, green = blue - 2, blue + 3
        if green == 6 and red >= 1:
            places.add(ordinal(red))
    return unique(places)


@check("ord-34-d3-4")
def o34_d3_4():
    white, yellow, red, green, blue = (f"the {colour} pencil" for colour in ("white", "yellow", "red", "green", "blue"))
    found = orders(
        [white, yellow, red, green, blue],
        lambda p: p[yellow] < p[red],
        lambda p: p[red] < p[green],
        lambda p: p[green] < p[blue],
        lambda p: p[white] < p[yellow],
    )
    return unique(order[2] for order in found)


@check("ord-34-d3-5")
def o34_d3_5():
    found = orders(
        ["Lena", "Masha", "Nadya", "Olya"],
        lambda p: p["Masha"] == 1,
        lambda p: 4 - p["Lena"] == 1,  # older than exactly one girl
        lambda p: p["Olya"] < p["Nadya"],
    )
    return unique(order[-1] for order in found)


@check("ord-34-d4-1")
def o34_d4_1():
    found = orders(
        ["Ann", "Ben", "Kim", "Dan", "Eva"],
        lambda p: p["Dan"] == 1,
        lambda p: p["Kim"] == p["Ben"] + 1,
        lambda p: p["Ann"] < p["Ben"],
        lambda p: abs(p["Kim"] - p["Ann"]) - 1 == 2,
    )
    return unique(ordinal(order.index("Eva") + 1) for order in found)


@check("ord-34-d4-2")
def o34_d4_2():
    chain = ["Vika", "Pavel", "Ruslan", "Semyon", "Timur", "Uliana"]
    found = orders(chain, *[lambda p, a=a, b=b: p[a] < p[b] for a, b in zip(chain, chain[1:])])
    return unique(order.index("Timur") - order.index("Vika") - 1 for order in found)


@check("ord-34-d4-3")
def o34_d4_3():
    maths, history, music, english, art = (f"the {name} book" for name in ("maths", "history", "music", "English", "art"))
    found = orders(
        [maths, history, music, english, art],
        lambda p: p[art] == 5,
        lambda p: abs(p[english] - p[art]) == 1,
        lambda p: p[history] == p[maths] + 1,
        lambda p: abs(p[music] - p[maths]) != 1,
    )
    return unique(order[2] for order in found)


@check("ord-34-d4-4")
def o34_d4_4():
    return unique(
        ordinal(front + 1) for front in range(7) for behind in range(7) if front + behind == 6 and front == 2 * behind
    )


@check("ord-34-d4-5")
def o34_d4_5():
    names = ["Ira", "Kolya", "Lida", "Misha"]
    heights = set()
    for values in permutations([128, 131, 134, 137]):
        height = dict(zip(names, values))
        if height["Ira"] > height["Kolya"] > height["Lida"] and height["Misha"] == 131 and height["Misha"] > height["Lida"]:
            heights.add(height["Ira"])
    return unique(heights)


@check("ord-34-d5-1")
def o34_d5_1():
    found = orders(
        ["Ann", "Ben", "Kim", "c1", "c2", "c3"],
        lambda p: p["Kim"] == 6,
        lambda p: abs(p["Ben"] - p["Kim"]) - 1 == 2,
        lambda p: abs(p["Ann"] - p["Ben"]) - 1 == 1,
        lambda p: p["Ann"] not in (1, 6),
    )
    return unique(ordinal(order.index("Ann") + 1) for order in found)


@check("ord-34-d5-2")
def o34_d5_2():
    found = orders(
        ["Eva", "Fedor", "Gosha", "Hanna", "Ivan"],
        lambda p: p["Eva"] not in (1, 5),
        lambda p: p["Fedor"] == p["Eva"] + 1,
        lambda p: p["Gosha"] < p["Eva"],
        lambda p: p["Ivan"] == p["Gosha"] + 1,
        lambda p: p["Hanna"] > p["Fedor"],
    )
    return unique(order[3] for order in found)


@check("ord-34-d5-3")
def o34_d5_3():
    found = orders(
        ["Lev", "Mira", "Nika", "Oleg"],
        lambda p: 4 - p["Lev"] == 2,  # taller than exactly two others
        lambda p: p["Lev"] < p["Mira"],
        lambda p: p["Mira"] < p["Nika"],
    )
    return unique(order[0] for order in found)


@check("ord-34-d5-4")
def o34_d5_4():
    found = orders(
        ["Kolya", "Dima", "r1", "r2", "r3", "r4"],
        lambda p: 6 - p["Kolya"] == 4,
        lambda p: p["Dima"] - 1 == 3,
    )
    return unique(abs(order.index("Dima") - order.index("Kolya")) - 1 for order in found)


@check("ord-34-d5-5")
def o34_d5_5():
    found = orders(
        ["red", "blue", "green", "white", "yellow"],
        lambda p: p["green"] == 2,
        lambda p: p["white"] == 5,
        lambda p: abs(p["white"] - p["red"]) != 1,
        lambda p: abs(p["yellow"] - p["green"]) == 1,
        lambda p: abs(p["red"] - p["blue"]) == 1,
    )
    return unique(order[2] for order in found)
