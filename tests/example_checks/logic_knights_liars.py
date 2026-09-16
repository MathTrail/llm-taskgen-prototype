"""Answer checks for data/examples/logic.knights_liars.json: every knight/liar assignment is tried."""

from itertools import product

from example_checks import check

IMPOSSIBLE = "It is impossible to tell"
PAIR = {
    (True, True): "Both are knights",
    (False, False): "Both are liars",
    (True, False): "Ann is a knight, Ben is a liar",
    (False, True): "Ann is a liar, Ben is a knight",
}


def only(candidates):
    candidates = list(candidates)
    assert len(candidates) == 1, candidates
    return candidates[0]


def worlds(names, says) -> list[dict]:
    """Every assignment (True = knight) in which each speaker's words are true exactly when the speaker is a knight."""
    found = []
    for kinds in product((True, False), repeat=len(names)):
        world = dict(zip(names, kinds))
        if all(words(world) == world[speaker] for speaker, words in says.items()):
            found.append(world)
    assert found, "no assignment fits"
    return found


def verdict(answers):
    answers = set(answers)
    return answers.pop() if len(answers) == 1 else IMPOSSIBLE


def pair(found):
    return verdict(PAIR[world["Ann"], world["Ben"]] for world in found)


def knights(found):
    return verdict(sum(world.values()) for world in found)


def circle(size, words) -> list[dict]:
    """Everyone at a round table says words(left, right) about their two neighbours."""
    seats = range(size)
    return worlds(seats, {seat: (lambda world, seat=seat: words(world[(seat - 1) % size], world[(seat + 1) % size])) for seat in seats})


@check("kl-34-d1-1")
def k34_d1_1():
    sentences = {
        "I am a knight.": lambda me: me,
        "I am a liar.": lambda me: not me,
        "2 + 2 = 4.": lambda me: True,
        "2 + 2 = 5.": lambda me: False,
        "I am not a liar.": lambda me: me,
    }
    return only(text for text, truth in sentences.items() if not any(truth(me) == me for me in (True, False)))


@check("kl-34-d1-2")
def k34_d1_2():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: 2 + 2 == 5, "Ben": lambda w: w["Ann"]}))


@check("kl-34-d1-3")
def k34_d1_3():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: True, "Ben": lambda w: not w["Ann"]}))


@check("kl-34-d1-4")
def k34_d1_4():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: not w["Ben"], "Ben": lambda w: 10 > 7}))


@check("kl-34-d1-5")
def k34_d1_5():
    def says_yes(me):
        truth = me  # "Are you a knight?"
        return truth if me else not truth

    answers = {
        (True, False): "Knights say yes, liars say no",
        (False, True): "Knights say no, liars say yes",
        (True, True): "Everybody says yes",
        (False, False): "Everybody says no",
    }
    return answers[says_yes(True), says_yes(False)]


@check("kl-34-d2-1")
def k34_d2_1():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: not w["Ann"] and not w["Ben"]}))


@check("kl-34-d2-2")
def k34_d2_2():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: not w["Ben"], "Ben": lambda w: w["Ben"]}))


@check("kl-34-d2-3")
def k34_d2_3():
    says = {"Ann": lambda w: not w["Ben"], "Ben": lambda w: not w["Kim"], "Kim": lambda w: 2 + 2 == 4}
    return knights(worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d2-4")
def k34_d2_4():
    says = {"Ann": lambda w: w["Ben"], "Ben": lambda w: w["Kim"], "Kim": lambda w: 2 + 2 == 5}
    return knights(worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d2-5")
def k34_d2_5():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: w["Ben"], "Ben": lambda w: w["Ann"] != w["Ben"]}))


@check("kl-34-d3-1")
def k34_d3_1():
    names = ["first", "second", "third"]
    return knights(worlds(names, {name: (lambda w: sum(w.values()) == 1) for name in names}))


@check("kl-34-d3-2")
def k34_d3_2():
    return knights(circle(4, lambda left, right: not left))


@check("kl-34-d3-3")
def k34_d3_3():
    says = {"Ann": lambda w: w["Ben"] and w["Kim"], "Ben": lambda w: not w["Kim"]}
    return knights(worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d3-4")
def k34_d3_4():
    return pair(worlds(["Ann", "Ben"], {"Ann": lambda w: not w["Ann"] or not w["Ben"]}))


@check("kl-34-d3-5")
def k34_d3_5():
    says = {"Ann": lambda w: not w["Ben"], "Ben": lambda w: not w["Kim"], "Kim": lambda w: not w["Ann"] and not w["Ben"]}
    return knights(worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d4-1")
def k34_d4_1():
    places = range(1, 6)
    return knights(worlds(places, {place: (lambda w, place=place: sum(not kind for kind in w.values()) == place) for place in places}))


@check("kl-34-d4-2")
def k34_d4_2():
    def liars(w):
        return sum(not kind for kind in w.values())

    says = {"Ann": lambda w: liars(w) == 1, "Ben": lambda w: liars(w) == 2, "Kim": lambda w: liars(w) == 3}
    return knights(worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d4-3")
def k34_d4_3():
    return knights(circle(5, lambda left, right: not left and not right))


@check("kl-34-d4-4")
def k34_d4_4():
    says = {"Ann": lambda w: not w["Ben"], "Ben": lambda w: not w["Ann"] and not w["Kim"], "Kim": lambda w: w["Ben"]}
    labels = {("Ann",): "only Ann", ("Ben",): "only Ben", ("Kim",): "only Kim", ("Ann", "Kim"): "Ann and Kim", (): "nobody"}
    return verdict(labels.get(tuple(name for name, kind in w.items() if kind), "other") for w in worlds(["Ann", "Ben", "Kim"], says))


@check("kl-34-d4-5")
def k34_d4_5():
    return knights(circle(6, lambda left, right: right and not left))


@check("kl-34-d5-1")
def k34_d5_1():
    return max(sum(w.values()) for w in circle(10, lambda left, right: not left and not right))


@check("kl-34-d5-2")
def k34_d5_2():
    places = range(12)
    return knights(worlds(places, {place: (lambda w, place=place: not w[place - 1]) for place in places if place > 0}))


@check("kl-34-d5-3")
def k34_d5_3():
    places = range(1, 7)
    return knights(worlds(places, {place: (lambda w, place=place: sum(not kind for kind in w.values()) >= place) for place in places}))


@check("kl-34-d5-4")
def k34_d5_4():
    labels = {
        (True, True): "Both are knights",
        (False, False): "Both are liars",
        (True, False): "Ben is a knight, Kim is a liar",
        (False, True): "Ben is a liar, Kim is a knight",
    }
    found = set()
    for ann, ben, kim, ann_said_liar in product((True, False), repeat=4):
        ann_truth = not ann if ann_said_liar else ann  # Ann said "I am a liar" or "I am a knight"
        if ann_truth == ann and ann_said_liar == ben and (not ben) == kim:
            found.add(labels[ben, kim])
    assert found
    return verdict(found)


@check("kl-34-d5-5")
def k34_d5_5():
    says = {
        "Ann": lambda w: not w["Ben"],
        "Ben": lambda w: not w["Kim"],
        "Kim": lambda w: not w["Dan"],
        "Dan": lambda w: not w["Ann"] and not w["Ben"],
    }
    return knights(worlds(["Ann", "Ben", "Kim", "Dan"], says))
