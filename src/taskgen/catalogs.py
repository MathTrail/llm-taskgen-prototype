"""Closed catalogs in data/catalogs/: loading and validation against schemas/catalogs/ (T08, SPEC 4.2, 4.4, 4.5).

Validate: uv run python -m taskgen.catalogs. Exit code 1 if any catalog is invalid.
"""

import json
import sys

from jsonschema import Draft202012Validator

from taskgen import ROOT

CATALOGS = ["topics", "skills", "traps"]


def load_catalog(name: str) -> list[dict]:
    """Entries of a catalog in data/catalogs/, e.g. load_catalog("traps")."""
    return json.loads((ROOT / "data" / "catalogs" / f"{name}.json").read_text(encoding="utf-8"))


def catalog_errors(name: str, entries: object) -> list[str]:
    """Schema violations and duplicate ids; an empty list means the catalog is valid."""
    schema = json.loads((ROOT / "schemas" / "catalogs" / f"{name}.json").read_text(encoding="utf-8"))
    errors = [
        f"{name}.json {'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(entries)
    ]
    if errors:
        return errors

    seen = set()
    for entry in entries:
        if entry["id"] in seen:
            errors.append(f"{name}.json: duplicate id {entry['id']!r}")
        seen.add(entry["id"])
    return errors


def main() -> None:
    failed = False
    for name in CATALOGS:
        try:
            entries = load_catalog(name)
        except json.JSONDecodeError as error:
            print(f"{name}.json: invalid JSON: {error}")
            failed = True
            continue

        errors = catalog_errors(name, entries)
        for error in errors:
            print(error)
        if not errors:
            print(f"{name}.json: {len(entries)} entries OK")
        failed = failed or bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
