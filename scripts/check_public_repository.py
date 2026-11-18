from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ENV_FILES = {".env.example"}
BINARY_SUFFIXES = {".gif", ".ico", ".jpeg", ".jpg", ".png", ".webp"}
FORBIDDEN_TEXT_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Stripe live key": re.compile(r"\b[sp]k_live_[A-Za-z0-9]{16,}\b"),
    "private staging host": re.compile(r"(?:devtunnels\.ms|up\.railway\.app)", re.IGNORECASE),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / path for path in result.stdout.decode().split("\0") if path]


def main() -> int:
    violations: list[str] = []

    for path in tracked_files():
        if not path.is_file():
            continue

        relative_path = path.relative_to(ROOT).as_posix()
        filename = path.name.lower()

        if filename == ".env" or (
            filename.startswith(".env.") and filename not in ALLOWED_ENV_FILES
        ):
            violations.append(f"tracked environment file: {relative_path}")
            continue

        if path.suffix.lower() in BINARY_SUFFIXES:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in FORBIDDEN_TEXT_PATTERNS.items():
            if pattern.search(content):
                violations.append(f"{label}: {relative_path}")

    if violations:
        print("Public repository check failed:")
        for violation in sorted(set(violations)):
            print(f"- {violation}")
        return 1

    print("Public repository check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
