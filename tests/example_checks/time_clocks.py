"""Answer checks for data/examples/time.clocks.json: times are counted minute by minute."""

from itertools import count

from example_checks import check

DAY = 24 * 60


def at(clock_time: str) -> int:
    """Minutes since midnight for a time written as H:MM."""
    hours, minutes = clock_time.split(":")
    return int(hours) * 60 + int(minutes)


def show(total: int) -> str:
    """Time of day written as H:MM on a 24-hour clock."""
    total %= DAY
    return f"{total // 60}:{total % 60:02d}"


def oclock(total: int) -> str:
    hour = (total // 60) % 12 or 12
    assert total % 60 == 0
    return f"{hour} o'clock"


def span(start: int, end: int) -> int:
    """Minutes that pass from start to end, going forward through midnight if needed."""
    passed, now = 0, start
    while now % DAY != end % DAY:
        now += 1
        passed += 1
    return passed


def duration(total: int) -> str:
    hours, minutes = divmod(total, 60)
    hour_text = f"{hours} hour{'s' if hours > 1 else ''}"
    if hours and minutes:
        return f"{hour_text} {minutes} minutes"
    return hour_text if hours else f"{minutes} minutes"


def strikes(start: int, end: int, half: bool = False, quarters: bool = False) -> int:
    """Strikes of a clock from start to end, both included: the hour count at full hours, 1 at the extra marks."""
    total = 0
    for now in range(start, end + 1):
        minute = now % 60
        if minute == 0:
            total += (now // 60) % 12 or 12
        elif half and minute == 30:
            total += 1
        elif quarters and minute in (15, 30, 45):
            total += 1
    return total


@check("clk-12-d1-1")
def c12_d1_1():
    return oclock(at("4:00") + 60)


@check("clk-12-d1-2")
def c12_d1_2():
    return oclock(at("12:00") - 2 * 60)


@check("clk-12-d1-3")
def c12_d1_3():
    return span(at("3:00"), at("5:00")) // 60


@check("clk-12-d1-4")
def c12_d1_4():
    return show(at("7:00") + 30)


@check("clk-12-d1-5")
def c12_d1_5():
    return show(at("10:00") + 45)


@check("clk-12-d2-1")
def c12_d2_1():
    return span(at("9:30"), at("10:00"))


@check("clk-12-d2-2")
def c12_d2_2():
    return span(at("21:00"), at("7:00")) // 60


@check("clk-12-d2-3")
def c12_d2_3():
    return show(at("5:45") + 15)


@check("clk-12-d2-4")
def c12_d2_4():
    return strikes(at("1:00"), at("4:00"))


@check("clk-12-d2-5")
def c12_d2_5():
    return show(at("8:20") - 10)


@check("clk-12-d3-1")
def c12_d3_1():
    return show(at("5:10") - 25)


@check("clk-12-d3-2")
def c12_d3_2():
    now = at("8:30")
    for lesson in range(1, 4):
        now += 40
        if lesson < 3:
            now += 10
    return show(now)


@check("clk-12-d3-3")
def c12_d3_3():
    return show(at("11:40") - 50)


@check("clk-12-d3-4")
def c12_d3_4():
    return max([3, 3, 3])  # the eggs boil at the same time


@check("clk-12-d3-5")
def c12_d3_5():
    return show(at("8:15") - 20)


@check("clk-12-d4-1")
def c12_d4_1():
    real = at("3:10") - 5
    return show(real - 5)


@check("clk-12-d4-2")
def c12_d4_2():
    return show(at("6:40") + 90)


@check("clk-12-d4-3")
def c12_d4_3():
    return strikes(at("9:00"), at("12:00"))


@check("clk-12-d4-4")
def c12_d4_4():
    return duration(span(at("4:50"), at("6:10")))


@check("clk-12-d4-5")
def c12_d4_5():
    return show(at("11:45") + 35)


@check("clk-12-d5-1")
def c12_d5_1():
    return strikes(at("1:15"), at("3:15"), half=True)


@check("clk-12-d5-2")
def c12_d5_2():
    now = at("3:00")
    for ride in range(1, 5):
        if ride > 1:
            now += 2
        now += 5
    return show(now)


@check("clk-12-d5-3")
def c12_d5_3():
    hours = span(at("8:00"), at("12:00")) // 60
    return show(at("12:00") + 2 * hours)


@check("clk-12-d5-4")
def c12_d5_4():
    return span(at("5:35"), at("7:15"))


@check("clk-12-d5-5")
def c12_d5_5():
    return show(at("4:50") + 60 + 25)


@check("clk-34-d1-1")
def c34_d1_1():
    return show(at("10:55") + 45)


@check("clk-34-d1-2")
def c34_d1_2():
    return duration(span(at("13:20"), at("15:05")))


@check("clk-34-d1-3")
def c34_d1_3():
    return 2 * 60 + 60 // 2


@check("clk-34-d1-4")
def c34_d1_4():
    return duration(span(at("21:30"), at("7:00")))


@check("clk-34-d1-5")
def c34_d1_5():
    return strikes(at("1:00"), at("12:00"))


@check("clk-34-d2-1")
def c34_d2_1():
    hours = span(at("9:00"), at("13:00")) // 60
    return show(at("13:00") - 3 * hours)


@check("clk-34-d2-2")
def c34_d2_2():
    departures = [at("6:00") + 12 * k for k in range(6)]
    return show(departures[5])


@check("clk-34-d2-3")
def c34_d2_3():
    return show(at("8:40") - (2 * 60 + 55))


@check("clk-34-d2-4")
def c34_d2_4():
    ends, now = [], at("8:00")
    while now < at("13:00"):
        now += 45
        ends.append(now)
        now += 10
    return sum(1 for end in ends if end < at("12:00"))


@check("clk-34-d2-5")
def c34_d2_5():
    return duration(span(at("22:40"), at("1:15")))


@check("clk-34-d3-1")
def c34_d3_1():
    start = at("12:15")
    return strikes(start, start + 12 * 60 - 1, half=True)


@check("clk-34-d3-2")
def c34_d3_2():
    real = at("10:02") - 7
    return show(real - 5)


@check("clk-34-d3-3")
def c34_d3_3():
    return show(at("21:30") - (60 + 50))


@check("clk-34-d3-4")
def c34_d3_4():
    return show(at("18:40") + 3 * 50)


@check("clk-34-d3-5")
def c34_d3_5():
    total = span(at("9:15"), at("11:45"))
    return next(lesson for lesson in range(1, 200) if 3 * lesson + 2 * 15 == total)


@check("clk-34-d4-1")
def c34_d4_1():
    shown = at("12:12") - at("8:00")
    real = next(minutes for minutes in range(1, 1000) if minutes * 63 == shown * 60)
    return show(at("8:00") + real)


@check("clk-34-d4-2")
def c34_d4_2():
    departures = range(at("6:10"), at("10:00"), 25)
    return sum(1 for time in departures if at("7:00") <= time <= at("9:00"))


@check("clk-34-d4-3")
def c34_d4_3():
    return show(at("14:25") + 100)


@check("clk-34-d4-4")
def c34_d4_4():
    for watch in range(at("8:00"), at("9:30")):
        believed = watch - 10  # he thinks the watch is 10 minutes fast
        if believed == at("8:40"):
            real = watch + 10  # but it is really 10 minutes slow
            return real + 20 - at("9:00")
    raise AssertionError("no departure found")


@check("clk-34-d4-5")
def c34_d4_5():
    return sum(1 for now in range(DAY) if len(set(f"{now // 60:02d}{now % 60:02d}")) == 1)


@check("clk-34-d5-1")
def c34_d5_1():
    return next(days for days in count(1) if (6 * days) % (12 * 60) == 0)


@check("clk-34-d5-2")
def c34_d5_2():
    return strikes(0, DAY - 1, quarters=True)


@check("clk-34-d5-3")
def c34_d5_3():
    swift = span(at("7:50"), at("10:35"))
    return show(at("8:20") + swift + 25)


@check("clk-34-d5-4")
def c34_d5_4():
    return sum(1 for now in range(DAY) if now // 60 == now % 60)


@check("clk-34-d5-5")
def c34_d5_5():
    week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    days = week.index("Friday") - week.index("Monday")
    return show(at("8:00") - (2 + 3 * days))
