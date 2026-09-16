"""Elo + IRT ratings and the difficulty corridor (SPEC 5.6).

P = GUESS + (1 - GUESS) * sigmoid(theta + delta - beta) is the chance that the student solves the task: theta is the
student's overall level, delta the offset for the task's topic, beta the task's difficulty. After an answer all three
move by K * (S - P), each with its own K = k0 / (1 + decay * n): its own k0 and its own count n of earlier answers
(the student's, the topic's, the task's). theta + delta is called the level here: the student's level in a topic.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from taskgen import ROOT

GUESS = 0.2  # five options and no penalty for a wrong answer
ELO_SCALE = 400 / math.log(10)  # R = 1500 + 173.7 * rating turns P's curve into the chess formula
DIFFICULTIES = range(1, 6)
FITS = ("inside", "too_hard", "too_easy")


@dataclass(frozen=True)
class Params:
    k0_student: float
    k0_topic: float
    k0_task: float
    decay: float
    corridor: tuple[float, float]  # bounds of P


def load_params(path: Path = ROOT / "config.yaml") -> Params:
    """The rating section of config.yaml."""
    rating = yaml.safe_load(path.read_text(encoding="utf-8"))["rating"]
    low, high = rating["corridor"]
    return Params(rating["k0_student"], rating["k0_topic"], rating["k0_task"], rating["decay"], (low, high))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def probability(level: float, beta: float) -> float:
    """Chance to solve a task of difficulty beta for a student whose level in the topic is theta + delta."""
    return GUESS + (1 - GUESS) * sigmoid(level - beta)


def k_factor(k0: float, decay: float, answers: int) -> float:
    """K = k0 / (1 + decay * n): big at first, so a rating settles fast, then smaller, so it stays stable."""
    return k0 / (1 + decay * answers)


def difficulty_to_beta(difficulty: int) -> float:
    """Starting beta of a task: 1 -> -2, 2 -> -1, 3 -> 0, 4 -> +1, 5 -> +2."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be 1-5, got {difficulty!r}")
    return float(difficulty - 3)


def elo(rating: float) -> float:
    """A rating (theta, theta + delta or beta) on the chess scale, for the console."""
    return 1500 + ELO_SCALE * rating


@dataclass(frozen=True)
class Update:
    probability: float  # P before the answer
    theta: float
    delta: float
    beta: float
    k_student: float
    k_topic: float
    k_task: float


def update(
    theta: float,
    delta: float,
    beta: float,
    *,
    correct: bool | None,
    student_answers: int,
    topic_answers: int,
    task_answers: int,
    params: Params,
) -> Update:
    """theta, delta and beta after one answer. S = 1 only for a correct answer; a wrong one and "?" (None) give 0.

    The answer counts are those before this answer; P is computed once from the old values.
    """
    p = probability(theta + delta, beta)
    error = (1 if correct is True else 0) - p
    k_student = k_factor(params.k0_student, params.decay, student_answers)
    k_topic = k_factor(params.k0_topic, params.decay, topic_answers)
    k_task = k_factor(params.k0_task, params.decay, task_answers)
    return Update(p, theta + k_student * error, delta + k_topic * error, beta - k_task * error, k_student, k_topic, k_task)


@dataclass(frozen=True)
class Corridor:
    beta_min: float  # beta range where P is inside the corridor: the bank searches it as is (SPEC 5.5)
    beta_max: float
    probabilities: dict[int, float]  # P for each difficulty 1-5 at its starting beta
    inside: list[int]  # difficulties whose P is inside the corridor: at most one, sometimes none
    recommended: int  # the difficulty whose P is closest to the middle of the corridor
    fit: str  # "inside", "too_hard" (its P is below the corridor) or "too_easy" (above)


def corridor(level: float, bounds: tuple[float, float]) -> Corridor:
    """Difficulty corridor for a student whose level in the topic is theta + delta (SPEC 5.6).

    The corridor is 0.96 wide on the beta scale and difficulties are 1 apart, so it holds at most one of them.
    The recommendation is therefore the difficulty whose P is closest to the middle of the corridor: the one inside
    if there is one, otherwise the nearest, marked too hard or too easy (D37).
    """
    low, high = bounds

    def logit(p):  # x = theta + delta - beta at which P equals p
        share = (p - GUESS) / (1 - GUESS)
        return math.log(share / (1 - share))

    probabilities = {difficulty: probability(level, difficulty_to_beta(difficulty)) for difficulty in DIFFICULTIES}
    middle = (low + high) / 2
    recommended = min(DIFFICULTIES, key=lambda difficulty: (abs(probabilities[difficulty] - middle), difficulty))
    p = probabilities[recommended]
    return Corridor(
        beta_min=level - logit(high),
        beta_max=level - logit(low),
        probabilities=probabilities,
        inside=[difficulty for difficulty, value in probabilities.items() if low <= value <= high],
        recommended=recommended,
        fit="inside" if low <= p <= high else "too_hard" if p < low else "too_easy",
    )


@dataclass
class Ratings:
    theta: float = 0.0
    answers: int = 0
    topics: dict[str, tuple[float, int]] = field(default_factory=dict)  # topic -> (delta, answers)


def replay_history(history: list[dict], params: Params) -> Ratings:
    """Ratings after the starting history, oldest row first, for a new student (SPEC 4.1, 5.6).

    Starting rows have no bank task: each one counts as a new task with beta = difficulty - 3 and no answers,
    and its new beta is not kept. Only theta and delta change (D37).
    """
    ratings = Ratings()
    for row in history:
        delta, topic_answers = ratings.topics.get(row["topic"], (0.0, 0))
        step = update(
            ratings.theta,
            delta,
            difficulty_to_beta(row["difficulty"]),
            correct=row["correct"],
            student_answers=ratings.answers,
            topic_answers=topic_answers,
            task_answers=0,
            params=params,
        )
        ratings.theta = step.theta
        ratings.answers += 1
        ratings.topics[row["topic"]] = (step.delta, topic_answers + 1)
    return ratings
