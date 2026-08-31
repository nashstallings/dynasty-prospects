"""Refuse a rebuilt dashboard export that looks half-published.

The scheduled refresh commits and deploys without anyone looking at it, so
this is the one thing standing between a truncated CFBD pull and the live
dashboard. It checks the shape a truncated upstream response actually takes
-- zero or oddly narrow prospects -- rather than trying to validate the data
itself.

    python -m dynasty_prospects.check_dashboard before.json after.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# A real pull spans a range of positions; a handful means something upstream
# truncated, not that the roster genuinely only has a few positions.
MIN_DISTINCT_POSITIONS = 5

# Prospect counts drift week to week as the pipeline reruns; they do not
# shed a tenth of the class overnight. A floor rather than a tight
# tolerance -- this is here to catch a broken file, not to have an opinion
# about roster churn.
MIN_PROSPECT_RATIO = 0.9


def check(before: dict[str, Any] | None, after: dict[str, Any]) -> list[str]:
    """Every reason to reject `after`, or an empty list if there are none."""
    problems = []
    prospects = after.get("prospects") or []

    if not prospects:
        problems.append("0 prospects in the rebuilt dashboard")
        return problems

    distinct_positions = {p.get("position") for p in prospects if p.get("position")}
    if len(distinct_positions) < MIN_DISTINCT_POSITIONS:
        problems.append(
            f"only {len(distinct_positions)} distinct positions present, expected at least {MIN_DISTINCT_POSITIONS}"
        )

    # A first build has nothing to compare against, and that is not a failure.
    if before is not None:
        was = len(before.get("prospects") or [])
        now = len(prospects)
        if was and now < was * MIN_PROSPECT_RATIO:
            problems.append(f"prospect count fell from {was} to {now}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)

    try:
        before = json.loads(args.before.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        before = None
    after = json.loads(args.after.read_text(encoding="utf-8"))

    problems = check(before, after)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{len(after['prospects'])} prospects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
