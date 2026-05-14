#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Convert stimulus_master_cdm_cat_v3.csv → stimuli.json for the static web version.

Usage:
    python3 convert_csv_to_json.py
"""

import json
import math
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
CSV = (SCRIPT_DIR / ".." / ".."
       / "Grammaticality_Judgement_CAT" / "stimuli" / "refined_cdm_cat"
       / "stimulus_master_cdm_cat_v3.csv").resolve()
OUT = SCRIPT_DIR / "stimuli.json"

COLS_TO_KEEP = [
    "item_id", "pair_id", "version", "item_type",
    "family_id", "family_name", "construct", "q_vector",
    "prime_text", "target_text", "target_lemma", "critical_region",
    "expected_response", "list_form",
    "run_assignment_A", "run_assignment_B",
    "trial_index_A", "trial_index_B",
]


def clean_val(v):
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    return v


def to_int_or_none(v):
    v = clean_val(v)
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def main():
    if not CSV.exists():
        raise SystemExit(f"CSV not found: {CSV}")
    df = pd.read_csv(CSV, dtype={"q_vector": str})
    df = df[COLS_TO_KEEP].copy()

    records = []
    for _, row in df.iterrows():
        rec = {}
        for c in COLS_TO_KEEP:
            v = row[c]
            if c in ("run_assignment_A", "run_assignment_B",
                     "trial_index_A", "trial_index_B"):
                rec[c] = to_int_or_none(v)
            else:
                rec[c] = clean_val(v)
        records.append(rec)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {len(records)} items to {OUT}")
    print(f"File size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
