"""PostgreSQL access: profiles, history, task bank, request and attempt logs (SPEC 7)."""

import os
import sys

from taskgen import ROOT


def database_url() -> str:
    """DATABASE_URL from the environment, otherwise from the .env file in the repository root."""
    if url := os.environ.get("DATABASE_URL"):
        return url
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "DATABASE_URL" and value.strip():
                return value.strip().strip("\"'")
    sys.exit("DATABASE_URL is not set: copy .env.example to .env")
