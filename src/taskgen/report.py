"""SPEC 9 metrics from the database in one command (T24).

  uv run python -m taskgen.report              # every request in the database
  uv run python -m taskgen.report --hours 24   # requests of the last 24 hours

Attempt metrics count the requests with at least one handed-in task; a request where the model got a package and
handed in nothing is counted apart (D45). Manual verdicts come from data/eval/reviews.json, written by the author:
  {"t-9d3191639994": {"verdict": "ok"},
   "t-e73f7b3c8108": {"verdict": "bad", "issues": ["age"], "note": "too long for grade 2"}}
The blind comparison of rule and model briefs is deferred (D45).
"""

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from taskgen import ROOT
from taskgen.db import database_url, request_answers
from taskgen.filters import load_thresholds
from taskgen.rating import load_params
from taskgen.service import answer_result

REVIEWS = ROOT / "data" / "eval" / "reviews.json"
VERDICTS = ("ok", "bad", "false_accept")  # false_accept: passed the checks but mathematically bad (SPEC 9)
ISSUES = (  # the manual review criteria of SPEC 9
    "unsolvable", "ambiguous", "not_olympiad", "age", "hint_gives_away", "unclear_traps", "implausible_distractors",
    "stereotypes",
)  # fmt: skip
MODES = ("rule", "llm")
TARGET_SECONDS = 90
MISSING = "-"

# The brief is the final one: for a generated task, the brief the model handed in with it.
# Prompt version and client come from the first attempt; bank requests have no attempts.
REQUESTS_SQL = """
SELECT r.request_id, r.created_at, r.student_id, r.tutor_mode, r.source, r.task_id, r.attempt_count, r.duration_ms,
       COALESCE(t.brief, r.brief) AS brief, a.prompt_version, a.models
FROM requests r
LEFT JOIN tasks t ON t.task_id = r.task_id AND r.source = 'generated'
LEFT JOIN LATERAL (
  SELECT prompt_version, models FROM attempts WHERE request_id = r.request_id ORDER BY attempt_no LIMIT 1
) a ON true
WHERE %(seconds)s::float8 IS NULL OR r.created_at > now() - make_interval(secs => %(seconds)s::float8)
ORDER BY r.created_at, r.request_id
"""

# The tasks the model wrote in the window; each is compared with the earlier ones of its topic (diversity).
TASKS_SQL = """
SELECT t.task_id, t.topic, t.skeptic,
       COALESCE((SELECT max(similarity(t.task ->> 'question', o.task ->> 'question'))
                 FROM tasks o
                 WHERE o.task_id = ANY(%(ids)s) AND o.topic = t.topic
                   AND (o.created_at, o.task_id) < (t.created_at, t.task_id)), 0) AS max_similarity
FROM tasks t
WHERE t.task_id = ANY(%(ids)s)
"""


def load(conn: psycopg.Connection, hours: float | None) -> tuple[list[dict], list[dict], dict[int, dict], list[dict]]:
    """Requests of the window, oldest first, with their attempts, answers and the tasks the model wrote."""
    seconds = None if hours is None else hours * 3600
    with conn.cursor(row_factory=dict_row) as cursor:
        requests = cursor.execute(REQUESTS_SQL, {"seconds": seconds}).fetchall()
        ids = [request["request_id"] for request in requests]
        attempts = cursor.execute("SELECT request_id, status, reason FROM attempts WHERE request_id = ANY(%s)",
                                  (ids,)).fetchall()  # fmt: skip
        written = [request["task_id"] for request in requests if request["source"] == "generated"]
        tasks = cursor.execute(TASKS_SQL, {"ids": written}).fetchall()
    for request in requests:
        models = request.pop("models")
        request["client"] = f"{models['name']} {models.get('version', '')}".strip() if models else None
    return requests, attempts, request_answers(conn, ids), tasks


# Counting


def attempt_stats(requests: list[dict], attempts: list[dict]) -> dict:
    """Counts behind the attempt metrics; `tried` are the requests with at least one handed-in task."""
    generated = [request for request in requests if request["source"] == "generated"]
    return {
        "requests": len(requests),
        "tried": sum(1 for request in requests if request["attempt_count"] > 0),
        "generated": len(generated),
        "accepted_on": Counter(request["attempt_count"] for request in generated),
        "abandoned": sum(1 for r in requests if r["source"] == "failed" and r["attempt_count"] == 0),
        "bank": sum(1 for request in requests if request["source"] == "bank"),
        "attempts": len(attempts),
        "reasons": Counter(attempt["reason"] for attempt in attempts if attempt["reason"]),
        "seconds": sorted(r["duration_ms"] / 1000 for r in generated if r["duration_ms"] is not None),
    }


def after_failure(requests: list[dict], answers: dict[int, dict]) -> dict[str, dict]:
    """For requests that follow a wrong answer or "?" of the same student: the goal of their brief and whether the
    brief uses the fresh trap_hit, by tutor mode (SPEC 9, adaptivity)."""
    found = {mode: {"goals": Counter(), "traps": 0, "used": 0} for mode in MODES}
    last_answer: dict[str, dict] = {}
    for request in requests:  # oldest first
        previous = last_answer.get(request["student_id"])
        if previous is not None and answer_result(previous) in ("wrong", "did not understand"):
            entry = found[request["tutor_mode"]]
            entry["goals"][request["brief"]["pedagogical_goal"]] += 1
            if previous["trap_hit"]:
                entry["traps"] += 1
                entry["used"] += previous["trap_hit"] in request["brief"]["traps_to_use"]
        answer = answers.get(request["request_id"])
        if answer is not None and answer_result(answer) != "not answered":
            last_answer[request["student_id"]] = answer
    return found


# Manual reviews


def review_errors(reviews: object) -> list[str]:
    if not isinstance(reviews, dict):
        return ["the file must hold an object: task_id -> review"]
    errors = []
    for task_id, review in reviews.items():
        if not isinstance(review, dict):
            errors.append(f"{task_id}: a review must be an object")
            continue
        if review.get("verdict") not in VERDICTS:
            errors.append(f"{task_id}: verdict must be one of {', '.join(VERDICTS)}")
        if unknown := set(review) - {"verdict", "issues", "note"}:
            errors.append(f"{task_id}: unknown fields {', '.join(sorted(unknown))}")
        issues = review.get("issues", [])
        if not isinstance(issues, list) or not all(issue in ISSUES for issue in issues):
            errors.append(f"{task_id}: issues must be a list of {', '.join(ISSUES)}")
        if not isinstance(review.get("note", ""), str):
            errors.append(f"{task_id}: note must be text")
    return errors


def load_reviews(path: Path = REVIEWS) -> dict[str, dict]:
    """The author's verdicts; no file means no reviews yet. Raises ValueError on a malformed file."""
    if not path.exists():
        return {}
    reviews = json.loads(path.read_text(encoding="utf-8"))
    if errors := review_errors(reviews):
        raise ValueError("; ".join(errors))
    return reviews


# Printing


def share(part: int, whole: int) -> str:
    return f"{part} of {whole}  {part / whole:.0%}" if whole else "no data"


def median_text(seconds: list[float]) -> str:
    return f"{statistics.median(seconds):.0f} s" if seconds else "no data"


def time_text(seconds: list[float]) -> str:
    """Median, 90th percentile (nearest rank) and how many are under the target; seconds are sorted."""
    if not seconds:
        return "no data"
    p90 = seconds[math.ceil(0.9 * len(seconds)) - 1]
    under = sum(1 for value in seconds if value < TARGET_SECONDS)
    return f"{median_text(seconds)} (p90 {p90:.0f} s; under {TARGET_SECONDS} s: {under} of {len(seconds)})"


def counts(counter: Counter) -> str:
    return ", ".join(f"{name} {count}" for name, count in counter.most_common()) or "none"


def table(rows: list[list[str]]) -> list[str]:
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return ["  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows]


def placement(correct: int, answered: int, bounds: tuple[float, float]) -> str:
    if not answered:
        return MISSING
    rate = correct / answered
    return "inside" if bounds[0] <= rate <= bounds[1] else "below" if rate < bounds[0] else "above"


def mode_lines(requests: list[dict], answers: dict[int, dict], bounds: tuple[float, float]) -> list[str]:
    """Correct answers by tutor mode against the corridor, then what the briefs did after a failure."""
    rows = [["mode", "requests", "answered", "correct", f"corridor {bounds[0]:.0%}-{bounds[1]:.0%}"]]
    for mode in MODES:
        chosen = [request for request in requests if request["tutor_mode"] == mode]
        results = [answer_result(answers[r["request_id"]]) for r in chosen if r["request_id"] in answers]
        answered = [result for result in results if result != "not answered"]
        correct = answered.count("correct")
        rows.append([mode, str(len(chosen)), str(len(answered)), share(correct, len(answered)),
                     placement(correct, len(answered), bounds)])  # fmt: skip
    lines = table(rows) + ['after a wrong answer or "?":']
    for mode, entry in after_failure(requests, answers).items():
        if entry["goals"]:
            lines.append(f"  {mode}: goals {counts(entry['goals'])}; "
                         f"fresh trap in the brief {share(entry['used'], entry['traps'])}")  # fmt: skip
    return lines if len(lines) > len(rows) + 1 else lines + ["  none yet"]


def breakdown(requests: list[dict], attempts: list[dict], key: str) -> list[str]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for request in requests:
        groups[request[key] or MISSING].append(request)
    attempts_of: dict[int, list[dict]] = defaultdict(list)
    for attempt in attempts:
        attempts_of[attempt["request_id"]].append(attempt)
    rows = [[key, "requests", "1st attempt", "within 3", "abandoned", "bank", "median time"]]
    for value, group in sorted(groups.items()):
        stats = attempt_stats(group, [attempt for r in group for attempt in attempts_of[r["request_id"]]])
        rows.append([value, str(stats["requests"]), share(stats["accepted_on"][1], stats["tried"]),
                     share(stats["generated"], stats["tried"]), str(stats["abandoned"]), str(stats["bank"]),
                     median_text(stats["seconds"])])  # fmt: skip
    return table(rows)


def report_lines(conn: psycopg.Connection, hours: float | None = None, reviews: dict | None = None) -> list[str]:
    """Every SPEC 9 metric, then the breakdowns by prompt version, tutor mode and client."""
    requests, attempts, answers, tasks = load(conn, hours)
    if not requests:
        return ["no requests in this window"]
    reviews = load_reviews() if reviews is None else reviews
    stats = attempt_stats(requests, attempts)
    accepted_on, reasons = stats["accepted_on"], stats["reasons"]
    threshold = load_thresholds().max_similarity
    written = [task["task_id"] for task in tasks]
    reviewed = [reviews[task_id] for task_id in written if task_id in reviews]
    verdicts = Counter(review["verdict"] for review in reviewed)
    minor = sum(1 for task in tasks
                if any(issue["severity"] == "minor" for issue in (task["skeptic"] or {}).get("issues", [])))  # fmt: skip
    unique = sum(1 for task in tasks if task["max_similarity"] < threshold)

    first, last = requests[0]["created_at"], requests[-1]["created_at"]
    lines = [f"SPEC 9 metrics: {len(requests)} requests from {first:%Y-%m-%d %H:%M} to {last:%Y-%m-%d %H:%M}", ""]
    lines += table([
        ["metric", "value", "target"],
        ["accepted on the 1st attempt", share(accepted_on[1], stats["tried"]), "> 50%"],
        ["accepted on the 2nd / 3rd attempt", f"{accepted_on[2]} / {accepted_on[3]}", ""],
        ["accepted within 3 attempts", share(stats["generated"], stats["tried"]), "> 80%"],
        ["abandoned: nothing handed in", str(stats["abandoned"]), "counted apart"],
        ["manual review: good", share(verdicts["ok"], len(reviewed)), "> 90%"],
        ["false accepts", share(verdicts["false_accept"], len(reviewed)), "0, at most 2%"],
        ["solver disagreed, of attempts", share(reasons["solver_disagrees"], stats["attempts"]), "watch"],
        ["blocking self-check, of attempts", share(reasons["self_check_blocking"], stats["attempts"]), "watch"],
        ["minor self-check notes, of accepted", share(minor, len(tasks)), "watch"],
        ["from the bank, of requests", share(stats["bank"], stats["requests"]), "watch"],
        ["unique plots within a topic", share(unique, len(tasks)), "> 80%"],
        ["time of a generated task, median", time_text(stats["seconds"]), f"< {TARGET_SECONDS} s"],
    ])  # fmt: skip
    fields = Counter(field for request in requests for field in request["brief"].get("profile_fields_used", []))
    issues = Counter(issue for review in reviewed for issue in review.get("issues", []))
    lines += [
        "",
        f"rejection reasons: {counts(reasons)}",
        f"profile fields used in {len(requests)} briefs: {counts(fields)}",
        f"manual review: {len(reviewed)} of {len(tasks)} written tasks reviewed; issues: {counts(issues)}",
    ]
    if outside := len(set(reviews) - set(written)):
        lines.append(f"  {outside} reviews are for tasks outside this report")

    lines += ["", "tutor modes (rule: the rule's brief; llm: changed by the model)"]
    lines += mode_lines(requests, answers, load_params().corridor)
    lines.append("blind comparison of rule and model briefs: deferred (D45)")

    by_topic: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for task in tasks:
        by_topic[task["topic"]][0] += 1
        by_topic[task["topic"]][1] += task["max_similarity"] < threshold
    lines += ["", f"diversity by topic (a near duplicate from similarity {threshold})"]
    lines += table([["topic", "tasks", "unique"]] + [[topic, str(total), share(fresh, total)]
                                                     for topic, (total, fresh) in sorted(by_topic.items())])  # fmt: skip
    for key in ("prompt_version", "tutor_mode", "client"):
        lines += ["", f"by {key}"] + breakdown(requests, attempts, key)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="SPEC 9 metrics from the database.")
    parser.add_argument("--hours", type=float, help="only requests of the last N hours (default: all)")
    args = parser.parse_args()
    try:
        reviews = load_reviews()
    except ValueError as error:
        sys.exit(f"data/eval/reviews.json: {error}")
    try:
        conn = psycopg.connect(database_url(), connect_timeout=5)
    except psycopg.OperationalError as error:
        sys.exit(f"cannot reach the database: {error.args[0].splitlines()[0]}; start it: docker compose up -d --wait")
    with conn:
        print("\n".join(report_lines(conn, args.hours, reviews)))


if __name__ == "__main__":
    main()
