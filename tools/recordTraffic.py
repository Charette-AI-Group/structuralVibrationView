r"""Append GitHub traffic numbers to traffic/traffic.csv.

GitHub keeps only the last 14 days of clone and view data and discards the
rest permanently, so this snapshots it into the repository where it
accumulates. Run weekly by .github/workflows/traffic.yml; it can also be
run by hand:

    .venv\Scripts\python.exe tools\recordTraffic.py

Authentication comes from GITHUB_TOKEN, falling back to the local
`gh auth token` so a manual run needs no setup. The traffic endpoints
require push access to the repository.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
csvFile = projectRoot / "traffic" / "traffic.csv"
columns = ("date", "clones", "uniqueCloners", "views", "uniqueVisitors")

defaultRepository = "Charette-AI-Group/structuralVibrationView"


def resolveToken() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        print(
            "No GITHUB_TOKEN, and `gh auth token` did not work.\n"
            "The traffic API needs a token with push access to the repository.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def fetchTraffic(repository: str, kind: str, token: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/traffic/{kind}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "frwb-traffic-recorder",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:200]
        print(f"GitHub returned {error.code} for traffic/{kind}: {detail}", file=sys.stderr)
        if error.code in (401, 403):
            print(
                "The traffic API requires push access. In Actions the default "
                "GITHUB_TOKEN may not be enough - see the note in "
                ".github/workflows/traffic.yml about using a PAT.",
                file=sys.stderr,
            )
        raise SystemExit(1) from None


def readExisting() -> dict[str, dict[str, str]]:
    if not csvFile.exists():
        return {}
    with csvFile.open(newline="", encoding="utf-8") as handle:
        return {row["date"]: row for row in csv.DictReader(handle)}


def mergeDay(rows: dict[str, dict[str, str]], date: str, values: dict[str, int]) -> None:
    row = rows.setdefault(date, dict.fromkeys(columns, "0") | {"date": date})
    # A later fetch supersedes an earlier one: the day may have been partial
    # when it was first recorded.
    row.update({key: str(value) for key, value in values.items()})


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", defaultRepository)
    token = resolveToken()

    clones = fetchTraffic(repository, "clones", token)
    views = fetchTraffic(repository, "views", token)

    rows = readExisting()
    before = len(rows)

    for day in clones.get("clones", []):
        mergeDay(
            rows,
            day["timestamp"][:10],
            {"clones": day["count"], "uniqueCloners": day["uniques"]},
        )
    for day in views.get("views", []):
        mergeDay(
            rows,
            day["timestamp"][:10],
            {"views": day["count"], "uniqueVisitors": day["uniques"]},
        )

    csvFile.parent.mkdir(parents=True, exist_ok=True)
    with csvFile.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for date in sorted(rows):
            writer.writerow(rows[date])

    print(f"{repository}: {len(rows)} days recorded ({len(rows) - before} new)")
    print(
        f"  last 14 days - clones {clones.get('count', 0)} "
        f"({clones.get('uniques', 0)} unique), "
        f"views {views.get('count', 0)} ({views.get('uniques', 0)} unique)"
    )
    print(f"  written to {csvFile.relative_to(projectRoot)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
