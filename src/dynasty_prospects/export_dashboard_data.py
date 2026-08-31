"""Join the pipeline's BigQuery tables into one flat data/dashboard.json for the web dashboard.

Only dim_prospect has a stable prospect_id -- every fact table is matched
back to it by normalized player name (see matching.py), since that's the
only thing they reliably share. fact_team_talent is the one exception: it's
team-level data with no player column at all, so it joins on team directly.

    python -m dynasty_prospects.export_dashboard_data
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from . import bigquery_io, config
from .matching import normalize_name

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "dashboard.json"


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> list of JSON-safe dicts (NaN/NaT become None)."""
    if df is None or df.empty:
        return []
    return df.astype(object).where(pd.notnull(df), None).to_dict("records")


def _with_norm_name(df: pd.DataFrame | None, name_col: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=[*((df.columns if df is not None else [])), "_norm_name"])
    out = df.copy()
    out["_norm_name"] = out[name_col].apply(normalize_name)
    return out


def _ambiguous_groups(df: pd.DataFrame, snapshot_cols: list[str], identity_cols: list[str]) -> set[str]:
    """norm_names where, within a single snapshot (one season, one recruiting
    class, one combine year, one source+date), more than one distinct real
    identity shares the same normalized name -- two different people, not
    one person's data spread across time (a transfer, a later snapshot)."""
    if df.empty:
        return set()
    ambiguous: set[str] = set()
    for _, snap in df.groupby(snapshot_cols):
        distinct = snap.drop_duplicates(subset=["_norm_name", *identity_cols])
        counts = distinct.groupby("_norm_name").size()
        ambiguous |= set(counts[counts > 1].index)
    return ambiguous


def build_dashboard(
    dim_prospect: pd.DataFrame,
    fact_recruiting: pd.DataFrame,
    fact_college_stats: pd.DataFrame,
    fact_team_talent: pd.DataFrame,
    fact_combine_testing: pd.DataFrame,
    fact_scouting_rankings: pd.DataFrame,
) -> dict[str, Any]:
    dim_prospect = dim_prospect if dim_prospect is not None else pd.DataFrame(
        columns=["player_name", "team", "draft_class", "prospect_id"]
    )
    dim_prospect = dim_prospect.copy()
    dim_prospect["_norm_name"] = dim_prospect["player_name"].apply(normalize_name)

    recruiting = _with_norm_name(fact_recruiting, "recruit_name")
    stats = _with_norm_name(fact_college_stats, "player_name")
    combine = _with_norm_name(fact_combine_testing, "player_name")
    scouting = _with_norm_name(fact_scouting_rankings, "player_name")
    talent = fact_team_talent.copy() if fact_team_talent is not None else pd.DataFrame(columns=["team", "season", "talent_composite"])

    # Ambiguous = two distinct people share a normalized name within a
    # single snapshot (same class year / season / combine year / source+date)
    # -- NOT a player who transferred or has multiple stat seasons, which is
    # the same person's data spread across rows and expected to accumulate.
    ambiguous_recruiting = _ambiguous_groups(recruiting, ["hs_class_year"], ["recruit_name", "committed_school"])
    ambiguous_stats = _ambiguous_groups(stats, ["season"], ["player_name", "team"])
    ambiguous_combine = _ambiguous_groups(combine, ["combine_year"], ["player_name", "school"])
    ambiguous_scouting = _ambiguous_groups(scouting, ["source", "snapshot_date"], ["player_name", "school"])

    unmatched_counts = {
        "fact_recruiting": 0,
        "fact_college_stats": 0,
        "fact_combine_testing": 0,
        "fact_scouting_rankings": 0,
    }
    matched_names = set(dim_prospect["_norm_name"])
    for label, table in (
        ("fact_recruiting", recruiting),
        ("fact_college_stats", stats),
        ("fact_combine_testing", combine),
        ("fact_scouting_rankings", scouting),
    ):
        if not table.empty:
            unmatched_counts[label] = int((~table["_norm_name"].isin(matched_names)).sum())

    prospects = []
    for _, row in dim_prospect.iterrows():
        norm_name = row["_norm_name"]
        team = row["team"]

        recruiting_rows = recruiting[recruiting["_norm_name"] == norm_name].drop(columns=["_norm_name"])
        stats_rows = stats[stats["_norm_name"] == norm_name].drop(columns=["_norm_name"]).sort_values("season") if not stats.empty else stats
        combine_rows = combine[combine["_norm_name"] == norm_name].drop(columns=["_norm_name"]) if not combine.empty else combine
        scouting_rows = (
            scouting[scouting["_norm_name"] == norm_name].drop(columns=["_norm_name"]).sort_values("snapshot_date", ascending=False)
            if not scouting.empty else scouting
        )
        talent_rows = talent[talent["team"] == team].sort_values("season") if not talent.empty else talent

        recruiting_records = _records(recruiting_rows)
        combine_records = _records(combine_rows)
        scouting_records = _records(scouting_rows)
        latest_scouting = scouting_records[0] if scouting_records else None

        # dim_prospect carries no position column of its own -- best effort
        # from whichever source table has one for this player.
        position = None
        for source in (recruiting_records, combine_records, scouting_records):
            if source and source[0].get("position"):
                position = source[0]["position"]
                break

        prospects.append({
            "prospect_id": row["prospect_id"],
            "player_name": row["player_name"],
            "team": team,
            "draft_class": row["draft_class"],
            "position": position,
            "recruiting": recruiting_records,
            "stats": _records(stats_rows),
            "talent": _records(talent_rows),
            "combine": combine_records,
            "scouting": scouting_records,
            "latest_rank": (latest_scouting["rank"] if latest_scouting is not None else None),
            "latest_tier": (latest_scouting["tier_grade"] if latest_scouting is not None else None),
            "ambiguous_match": bool(
                norm_name in ambiguous_recruiting
                or norm_name in ambiguous_stats
                or norm_name in ambiguous_combine
                or norm_name in ambiguous_scouting
            ),
        })

    for label, count in unmatched_counts.items():
        total = len(recruiting) if label == "fact_recruiting" else (
            len(stats) if label == "fact_college_stats" else (
                len(combine) if label == "fact_combine_testing" else len(scouting)
            )
        )
        if total:
            print(f"{count} of {total} {label} rows unmatched to a prospect")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "draft_class": config.DRAFT_CLASS,
        "prospects": prospects,
    }


def _without_timestamp(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "generated_at"}


def _changed(new_payload: dict[str, Any], out_path: Path) -> bool:
    if not out_path.exists():
        return True
    try:
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    return _without_timestamp(existing) != _without_timestamp(new_payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    payload = build_dashboard(
        dim_prospect=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "dim_prospect"),
        fact_recruiting=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "fact_recruiting"),
        fact_college_stats=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "fact_college_stats"),
        fact_team_talent=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "fact_team_talent"),
        fact_combine_testing=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "fact_combine_testing"),
        fact_scouting_rankings=bigquery_io.read_table(config.PROJECT_ID, config.DATASET_ID, "fact_scouting_rankings"),
    )

    if not _changed(payload, args.out):
        print(f"{args.out} unchanged, not writing")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {len(payload['prospects']):,} prospects to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
