"""rating.py against the worked example in docs/architecture/05-ratings.md (T05) and the corridor rules of D37."""

import math

import pytest

from taskgen import rating
from taskgen.rating import Params

# The T05 example uses one K0 = 0.4 for all three parameters.
T05 = Params(k0_student=0.4, k0_topic=0.4, k0_task=0.4, decay=0.05, corridor=(0.70, 0.85))
TOPIC = "combinatorics.enumeration"

# Table "Все шаги": difficulty, answer, P, S - P, K student = K topic, K task, theta, delta, beta after.
STEPS = [
    (2, True, 0.7848, 0.2152, 0.4000, 0.4000, 0.0861, 0.0861, -1.0861),
    (3, False, 0.6343, -0.6343, 0.3810, 0.4000, -0.1556, -0.1556, 0.2537),
    (3, None, 0.5383, -0.5383, 0.3636, 0.4000, -0.3513, -0.3513, 0.2153),
]

# Table "Коридор после каждого шага": theta + delta, R by theta, beta corridor, P for difficulties 1-5, difficulty inside.
CORRIDORS = [
    (0.0, 1500, (-1.466, -0.511), (0.905, 0.785, 0.600, 0.415, 0.295), 2),
    (0.172, 1515, (-1.294, -0.339), (0.918, 0.811, 0.634, 0.443, 0.311), 2),
    (-0.311, 1473, (-1.778, -0.822), (0.875, 0.733, 0.538, 0.370, 0.272), 2),
    (-0.703, 1439, (-2.169, -1.213), (0.828, 0.659, 0.465, 0.323, 0.250), 1),
]

# Table "Сложность → β → P": P for theta = -1, 0, +1 with delta = 0.
PROBABILITIES = {
    1: (0.785, 0.905, 0.962),
    2: (0.600, 0.785, 0.905),
    3: (0.415, 0.600, 0.785),
    4: (0.295, 0.415, 0.600),
    5: (0.238, 0.295, 0.415),
}


def t05_steps():
    """Run the T05 example: a new student, three new tasks of one topic."""
    theta = delta = 0.0
    for answers, (difficulty, correct, *_expected) in enumerate(STEPS):
        step = rating.update(theta, delta, rating.difficulty_to_beta(difficulty), correct=correct,
                             student_answers=answers, topic_answers=answers, task_answers=0, params=T05)
        theta, delta = step.theta, step.delta
        yield step


def test_t05_steps():
    for step, (_, correct, p, error, k, k_task, theta, delta, beta) in zip(t05_steps(), STEPS, strict=True):
        assert step.probability == pytest.approx(p, abs=1e-4)
        assert (1 if correct else 0) - step.probability == pytest.approx(error, abs=1e-4)
        assert step.k_student == pytest.approx(k, abs=1e-4)
        assert step.k_topic == pytest.approx(k, abs=1e-4)
        assert step.k_task == pytest.approx(k_task, abs=1e-4)
        assert (step.theta, step.delta, step.beta) == pytest.approx((theta, delta, beta), abs=1e-4)


def test_t05_corridor_after_each_step():
    thetas = [0.0] + [step.theta for step in t05_steps()]
    for theta, (level, elo, betas, probabilities, inside) in zip(thetas, CORRIDORS, strict=True):
        assert 2 * theta == pytest.approx(level, abs=5e-4)  # theta and delta move together in the example
        assert rating.elo(theta) == pytest.approx(elo, abs=0.5)
        found = rating.corridor(2 * theta, T05.corridor)
        assert (found.beta_min, found.beta_max) == pytest.approx(betas, abs=5e-4)
        assert tuple(found.probabilities[difficulty] for difficulty in rating.DIFFICULTIES) == pytest.approx(
            probabilities, abs=5e-4
        )
        assert found.inside == [inside]
        assert (found.recommended, found.fit) == (inside, "inside")


def test_t05_difficulty_table():
    for difficulty, row in PROBABILITIES.items():
        beta = rating.difficulty_to_beta(difficulty)
        assert beta == difficulty - 3
        for theta, expected in zip((-1, 0, 1), row, strict=True):
            assert rating.probability(theta, beta) == pytest.approx(expected, abs=5e-4)
    assert [round(rating.elo(theta)) for theta in (-1, 0, 1)] == [1326, 1500, 1674]


def test_corridor_bounds_on_x():
    found = rating.corridor(0.0, (0.70, 0.85))
    assert (-found.beta_max, -found.beta_min) == pytest.approx((0.5108, 1.4663), abs=1e-4)
    assert rating.probability(0.0, found.beta_min) == pytest.approx(0.85)
    assert rating.probability(0.0, found.beta_max) == pytest.approx(0.70)


def test_empty_corridor_recommends_the_closest_difficulty():
    found = rating.corridor(0.5, (0.70, 0.85))  # remark 05-1: neither -1 nor 0 is in [-0.97, -0.01]
    assert found.inside == []
    assert found.probabilities[2] == pytest.approx(0.854, abs=5e-4)
    assert found.probabilities[3] == pytest.approx(0.698, abs=5e-4)
    assert (found.recommended, found.fit) == (3, "too_hard")  # 0.698 is nearer to 0.775 than 0.854


def test_very_weak_and_very_strong_students():
    weak = rating.corridor(-2.0, (0.70, 0.85))
    assert (weak.inside, weak.recommended, weak.fit) == ([], 1, "too_hard")
    strong = rating.corridor(4.0, (0.70, 0.85))
    assert (strong.inside, strong.recommended, strong.fit) == ([], 5, "too_easy")


def test_corridor_holds_at_most_one_difficulty_and_recommends_it():
    for step in range(-400, 601):
        found = rating.corridor(step / 100, (0.70, 0.85))
        assert len(found.inside) <= 1
        if found.inside:
            assert (found.recommended, found.fit) == (found.inside[0], "inside")
        assert found.fit in rating.FITS


def test_elo_scale_gives_the_chess_formula():
    for theta, beta in [(0.0, 0.0), (0.7, -1.0), (-1.2, 2.0)]:
        chess = 1 / (1 + 10 ** ((rating.elo(beta) - rating.elo(theta)) / 400))
        assert chess == pytest.approx(rating.sigmoid(theta - beta))


def test_k_decreases_with_answers():
    ks = [rating.k_factor(0.4, 0.05, answers) for answers in range(30)]
    assert ks[0] == 0.4 and all(earlier > later for earlier, later in zip(ks, ks[1:]))


def test_difficulty_outside_1_to_5_is_rejected():
    for difficulty in (0, 6):
        with pytest.raises(ValueError):
            rating.difficulty_to_beta(difficulty)


def test_each_parameter_has_its_own_k0():
    params = Params(k0_student=0.2, k0_topic=0.4, k0_task=0.3, decay=0.05, corridor=(0.70, 0.85))
    step = rating.update(0.0, 0.0, -1.0, correct=True, student_answers=0, topic_answers=0, task_answers=0,
                         params=params)
    error = 1 - step.probability
    assert (step.theta, step.delta, step.beta) == pytest.approx((0.2 * error, 0.4 * error, -1 - 0.3 * error))


def test_config_values():
    params = rating.load_params()
    assert params == Params(k0_student=0.2, k0_topic=0.4, k0_task=0.4, decay=0.05, corridor=(0.70, 0.85))


def test_replay_history_matches_the_t05_example():
    history = [{"topic": TOPIC, "difficulty": difficulty, "correct": correct} for difficulty, correct, *_ in STEPS]
    ratings = rating.replay_history(history, T05)
    assert ratings.theta == pytest.approx(-0.3513, abs=1e-4)
    assert ratings.answers == 3
    assert ratings.topics.keys() == {TOPIC}
    delta, answers = ratings.topics[TOPIC]
    assert (delta, answers) == (pytest.approx(-0.3513, abs=1e-4), 3)


def test_replay_history_keeps_topics_apart():
    params = rating.load_params()
    history = [
        {"topic": TOPIC, "difficulty": 2, "correct": True},
        {"topic": "time.clocks", "difficulty": 3, "correct": False},
    ]
    ratings = rating.replay_history(history, params)

    first = rating.update(0, 0, -1, correct=True, student_answers=0, topic_answers=0, task_answers=0, params=params)
    second = rating.update(first.theta, 0, 0, correct=False, student_answers=1, topic_answers=0, task_answers=0,
                           params=params)
    assert ratings.theta == pytest.approx(second.theta)
    assert ratings.answers == 2
    assert ratings.topics == {TOPIC: (pytest.approx(first.delta), 1), "time.clocks": (pytest.approx(second.delta), 1)}


def test_replay_of_empty_history():
    assert rating.replay_history([], rating.load_params()) == rating.Ratings()


def test_probability_has_the_guessing_floor():
    assert rating.probability(-50, 0) == pytest.approx(0.2)
    assert rating.probability(50, 0) == pytest.approx(1.0)
    assert math.isclose(rating.probability(0, 0), 0.6)
