"""Public-hygiene check for pull requests.

Scans what a PR would add to the public repo (added diff lines, commit
messages and the PR title) and fails on any hit. Commit author and
committer emails are not checked.

The pattern lists are deliberately not in this repo. They come from the
HYGIENE_PATTERNS secret: a JSON object mapping a category name to a regular
expression, matched against lowercased text. Findings name the category
and location only, never the pattern or the matched text.

Usage: hygiene_scan.py BASE_SHA HEAD_SHA

Environment:
  HYGIENE_PATTERNS    JSON {category: regex}. Required unless skipping is allowed.
  HYGIENE_ALLOW_SKIP  "1" where secrets are unavailable (fork and Dependabot
                      PRs); the scan is then skipped instead of failing.
  PR_TITLE            Optional. Scanned like a commit message, since it ends
                      up in the merge commit.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# Vendored third-party data and lockfiles are not ours to police.
SKIP_PATHS = re.compile(r"(vendor/maxdiff/|tools/maxdiff/|uv\.lock$)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def is_noreply(email: str) -> bool:
    local, _, domain = email.strip().lower().rpartition("@")
    return domain == "users.noreply.github.com" or local == "noreply"


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        check=True,
        capture_output=True,
    ).stdout
    return out.decode("utf-8", "replace")


def escape(value: str, prop: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def report(message: str, path: str | None = None, line: int | None = None) -> None:
    props = []
    if path:
        props.append(f"file={escape(path, prop=True)}")
    if line:
        props.append(f"line={line}")
    props.append("title=Public hygiene")
    print(f"::error {','.join(props)}::{escape(message)}")


def added_lines(base: str, head: str):
    """Yield (path, line_number, text) for every line the PR adds."""
    diff = git(
        "diff",
        "--no-color",
        "--no-ext-diff",
        "-M",
        "--unified=0",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        f"{base}...{head}",
    )
    path: str | None = None
    lineno = 0
    in_header = False
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            in_header, path = True, None
        elif in_header:
            if raw.startswith("+++ "):
                target = raw[4:].strip('"')
                path = None if target == "/dev/null" else target.removeprefix("b/")
            elif m := HUNK.match(raw):
                in_header, lineno = False, int(m.group(1))
        elif m := HUNK.match(raw):
            lineno = int(m.group(1))
        elif raw.startswith("+"):
            if path and not SKIP_PATHS.search(path):
                yield path, lineno, raw[1:]
            lineno += 1


def commits(base: str, head: str):
    """Yield (sha, author_email, committer_email, message) for the PR's commits."""
    log = git("log", "--no-color", "--format=%H%x00%ae%x00%ce%x00%B%x01", f"{base}..{head}")
    for rec in log.split("\x01"):
        rec = rec.strip("\n")
        if rec:
            sha, author, committer, body = rec.split("\x00", 3)
            yield sha, author, committer, body


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    base, head = sys.argv[1], sys.argv[2]

    raw = os.environ.get("HYGIENE_PATTERNS", "").strip()
    if not raw:
        if os.environ.get("HYGIENE_ALLOW_SKIP") == "1":
            print(
                "::notice title=Public hygiene::Skipped: the patterns secret isn't "
                "available to this PR (fork or Dependabot)."
            )
            return 0
        report("The HYGIENE_PATTERNS secret is missing or empty.")
        return 1
    try:
        patterns = {str(k): re.compile(v) for k, v in json.loads(raw).items()}
    except (ValueError, AttributeError, TypeError, re.error):
        report("HYGIENE_PATTERNS is not a JSON object of valid regular expressions.")
        return 1

    def categories(text: str) -> list[str]:
        lowered = text.lower()
        return [name for name, pat in patterns.items() if pat.search(lowered)]

    failures = 0
    nlines = 0
    files: set[str] = set()
    for path, lineno, text in added_lines(base, head):
        nlines += 1
        files.add(path)
        for name in categories(text):
            report(f"Added line matches the '{name}' list.", path, lineno)
            failures += 1

    ncommits = 0
    for sha, _author, _committer, body in commits(base, head):
        ncommits += 1
        short = sha[:8]
        for name in categories(body):
            report(f"Commit {short}: message matches the '{name}' list.")
            failures += 1
        if any(not is_noreply(e) for e in EMAIL.findall(body)):
            report(
                f"Commit {short}: message contains an email address that isn't a noreply address."
            )
            failures += 1

    title = os.environ.get("PR_TITLE", "")
    for name in categories(title):
        report(f"PR title matches the '{name}' list.")
        failures += 1

    print(
        f"Scanned {nlines} added lines in {len(files)} files and {ncommits} commits "
        f"against {len(patterns)} pattern lists: {failures} finding(s)."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
