"""Repair tri-state final-stage truncation metadata in the 160-item audit table.

The frozen audit key stores ``stage_truncated=null`` for every final picker or
aggregator record.  The original item-level export coerced those nulls to
``false``.  This narrow repair restores ``NA`` and recomputes ``any_truncated``
with three-valued OR semantics without changing labels or transition fields.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "analysis/final_transition_endorsement_audit/unblind/item_level_unblinded_160.csv"
KEY = ROOT / "analysis/final_transition_endorsement_audit/final_transition_audit_key.jsonl"


def parse_bool(value: str) -> bool | None:
    value = value.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    if value in {"", "na", "null", "none"}:
        return None
    raise ValueError(f"unexpected Boolean value: {value!r}")


def format_bool(value: bool | None) -> str:
    if value is None:
        return "NA"
    return "true" if value else "false"


def tri_or(values: list[bool | None]) -> bool | None:
    if any(value is True for value in values):
        return True
    if any(value is None for value in values):
        return None
    return False


def main() -> None:
    key_rows = [json.loads(line) for line in KEY.read_text(encoding="utf-8").splitlines() if line.strip()]
    finals_by_item: dict[str, list[dict]] = defaultdict(list)
    for row in key_rows:
        if row.get("in_item_analysis") is True and row.get("position") == "final":
            finals_by_item[str(row["item_blind_id"])].append(row)

    with ITEMS.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    if len(rows) != 160:
        raise ValueError(f"expected 160 audit items, found {len(rows)}")
    for row in rows:
        item_id = row["item_blind_id"]
        finals = finals_by_item[item_id]
        if len(finals) != 1:
            raise ValueError(f"{item_id}: expected one analysis final stage, found {len(finals)}")
        final_value = finals[0].get("stage_truncated")
        if final_value not in {True, False, None}:
            raise ValueError(f"{item_id}: unexpected key truncation value {final_value!r}")
        row["final_truncated"] = format_bool(final_value)
        row["any_truncated"] = format_bool(
            tri_or([
                parse_bool(row["question_any_truncated"]),
                parse_bool(row["source_truncated"]),
                final_value,
            ])
        )

    with ITEMS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    missing_final = sum(row["final_truncated"] == "NA" for row in rows)
    missing_any = sum(row["any_truncated"] == "NA" for row in rows)
    print(f"repaired {ITEMS}: final_truncated NA={missing_final}; any_truncated NA={missing_any}")


if __name__ == "__main__":
    main()
