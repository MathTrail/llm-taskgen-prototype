"""Answer checks for data/examples/time.calendar.json: days are stepped one by one, ages are searched year by year."""

import calendar
from datetime import date, timedelta

from example_checks import check

WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def shift(day: str, days: int) -> str:
    """Day of the week after stepping the given number of days forward (or back if negative)."""
    index, step = WEEK.index(day), 1 if days >= 0 else -1
    for _ in range(abs(days)):
        index = (index + step) % 7
    return WEEK[index]


def month(first_day: str, length: int) -> list[str]:
    """Days of the week of every date in a month that starts on first_day."""
    return [shift(first_day, n) for n in range(length)]


@check("cal-12-d1-1")
def k12_d1_1():
    return shift("Monday", 2)


@check("cal-12-d1-2")
def k12_d1_2():
    age = 6
    for _ in range(3):
        age += 1
    return age


@check("cal-12-d1-3")
def k12_d1_3():
    return shift("Friday", 1)


@check("cal-12-d1-4")
def k12_d1_4():
    return len(range(7 * 2))


@check("cal-12-d1-5")
def k12_d1_5():
    return 8 - 5


@check("cal-12-d2-1")
def k12_d2_1():
    return shift("Wednesday", -3)


@check("cal-12-d2-2")
def k12_d2_2():
    return next(now for now in range(50) if now + 4 == 11)


@check("cal-12-d2-3")
def k12_d2_3():
    day, days = "Monday", 1
    while day != "Sunday":
        day = shift(day, 1)
        days += 1
    return days


@check("cal-12-d2-4")
def k12_d2_4():
    return (date(2023, 5, 5) - date(2023, 4, 28)).days


@check("cal-12-d2-5")
def k12_d2_5():
    grandpa, dad = 60, 35
    while dad > 0:
        grandpa, dad = grandpa - 1, dad - 1
    return grandpa


@check("cal-12-d3-1")
def k12_d3_1():
    return shift("Tuesday", 10)


@check("cal-12-d3-2")
def k12_d3_2():
    ben = next(now for now in range(50) if now + 5 == 12)
    return ben + 3


@check("cal-12-d3-3")
def k12_d3_3():
    return month("Monday", 30)[15 - 1]


@check("cal-12-d3-4")
def k12_d3_4():
    return len(range(2, 30 + 1, 3))


@check("cal-12-d3-5")
def k12_d3_5():
    return next(year for year in range(2019, 2100) if year - 2019 == 10)


@check("cal-12-d4-1")
def k12_d4_1():
    return shift("Sunday", 20)


@check("cal-12-d4-2")
def k12_d4_2():
    sums = {(a + 3) + (15 - a + 3) for a in range(1, 15)}
    assert len(sums) == 1
    return sums.pop()


@check("cal-12-d4-3")
def k12_d4_3():
    return month("Saturday", 31).count("Sunday")


@check("cal-12-d4-4")
def k12_d4_4():
    return next(years for years in range(1, 100) if 29 + years == 3 * (5 + years))


@check("cal-12-d4-5")
def k12_d4_5():
    trip = [shift("Thursday", n) for n in range(5)]
    return trip[-1]


@check("cal-12-d5-1")
def k12_d5_1():
    return shift("Friday", -100)


@check("cal-12-d5-2")
def k12_d5_2():
    return next(8 + years for years in range(50) if 8 + years == 2 * (3 + years))


@check("cal-12-d5-3")
def k12_d5_3():
    return shift("Monday", 31)


@check("cal-12-d5-4")
def k12_d5_4():
    return next(twin + 5 for twin in range(30) if 2 * twin + (twin + 5) == 23)


@check("cal-12-d5-5")
def k12_d5_5():
    return shift("Wednesday", 365)


@check("cal-34-d1-1")
def k34_d1_1():
    return shift("Thursday", 15)


@check("cal-34-d1-2")
def k34_d1_2():
    return next(times for times in range(1, 20) if 9 * times == 36)


@check("cal-34-d1-3")
def k34_d1_3():
    return sum(calendar.monthrange(2023, month_number)[1] for month_number in (3, 4, 5))


@check("cal-34-d1-4")
def k34_d1_4():
    return sum(1 for start in range(0, 366, 7) if start + 7 <= 366)


@check("cal-34-d1-5")
def k34_d1_5():
    return 2026 - 1958


@check("cal-34-d2-1")
def k34_d2_1():
    return shift("Monday", 30)


@check("cal-34-d2-2")
def k34_d2_2():
    now = 7 + 3
    return now + 4


@check("cal-34-d2-3")
def k34_d2_3():
    return (date(2023, 7, 5) - date(2023, 6, 25)).days + 1


@check("cal-34-d2-4")
def k34_d2_4():
    return next(petya for petya in range(1, 50) if petya + 4 * petya == 40)


@check("cal-34-d2-5")
def k34_d2_5():
    wednesdays = [n + 1 for n, day in enumerate(month("Sunday", 31)) if day == "Wednesday"]
    return wednesdays[2]


@check("cal-34-d3-1")
def k34_d3_1():
    return shift("Tuesday", (date(2023, 6, 1) - date(2023, 3, 1)).days)


@check("cal-34-d3-2")
def k34_d3_2():
    brother = next(b for b in range(1, 50) if 3 * b + 4 == 2 * (b + 4))
    return 3 * brother


@check("cal-34-d3-3")
def k34_d3_3():
    return max(month(first, length).count("Saturday") for first in WEEK for length in range(28, 32))


@check("cal-34-d3-4")
def k34_d3_4():
    return sum(1 for year in range(2017, 2032 + 1) if calendar.isleap(year))


@check("cal-34-d3-5")
def k34_d3_5():
    today = shift("Thursday", 2)
    return shift(today, 2)


@check("cal-34-d4-1")
def k34_d4_1():
    return shift("Friday", (date(2023, 12, 31) - date(2023, 1, 1)).days)


@check("cal-34-d4-2")
def k34_d4_2():
    return next(years for years in range(100) if (5 + years) + (8 + years) + (11 + years) == 60)


@check("cal-34-d4-3")
def k34_d4_3():
    firsts = set()
    for first in WEEK:
        for length in range(28, 32):
            days = month(first, length)
            counts = {day: days.count(day) for day in WEEK}
            if counts["Friday"] == counts["Saturday"] == 5 and counts["Thursday"] == counts["Sunday"] == 4:
                firsts.add(first)
    assert len(firsts) == 1, firsts
    return firsts.pop()


@check("cal-34-d4-4")
def k34_d4_4():
    return next(masha for masha in range(1, 50) if 7 * masha + 5 == 5 * (masha + 5))


@check("cal-34-d4-5")
def k34_d4_5():
    start = date(2024, 10, 26)
    assert start.strftime("%A") == "Saturday"
    end = start + timedelta(days=9 - 1)
    return f"{end:%A}, {end.day} {end:%B}"


@check("cal-34-d5-1")
def k34_d5_1():
    assert date(2026, 1, 1).strftime("%A") == "Thursday"
    return shift("Thursday", (date(2029, 1, 1) - date(2026, 1, 1)).days)


@check("cal-34-d5-2")
def k34_d5_2():
    return next(boy for boy in range(1, 65) if boy + 12 * boy == 65)


@check("cal-34-d5-3")
def k34_d5_3():
    assert date(2026, 3, 10).strftime("%A") == "Tuesday"
    return shift("Tuesday", (date(2026, 5, 10) - date(2026, 3, 10)).days)


@check("cal-34-d5-4")
def k34_d5_4():
    return next(youngest + 3 for youngest in range(50) if sum(youngest + k for k in range(4)) == 42)


@check("cal-34-d5-5")
def k34_d5_5():
    first = date(2028, 1, 1)
    assert calendar.isleap(2028) and first.strftime("%A") == "Saturday"
    return sum(1 for n in range(366) if (first + timedelta(days=n)).strftime("%A") == "Saturday")
