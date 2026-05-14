#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Forced Alignment Helper — Extract critical-word onset times from TTS audio.

For each target audio file (e.g., P001G.wav), run forced alignment to obtain
word-level onset times, then identify the critical region words and append
`critical_word_onset_ms_aligned` + `critical_word_duration_ms_aligned`
columns to the master CSV.

Supported backends:
- whisperX (pip install whisperx; requires CUDA optional)
- Gentle (Docker-based; requires `docker run lowerquality/gentle`)
- Manual JSON (read pre-computed alignment JSON from --json-dir)

Usage:
    # whisperX (default, auto-detects CUDA)
    python3 forced_align_audio.py --backend whisperx

    # Just print alignments without updating CSV
    python3 forced_align_audio.py --backend whisperx --dry-run

    # Specific items only
    python3 forced_align_audio.py --backend whisperx --items P001G,P001U

    # If alignments already in JSON files
    python3 forced_align_audio.py --backend json --json-dir alignments/
"""

import argparse
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
CSV = (SCRIPT_DIR / ".." / ".."
       / "Grammaticality_Judgement_CAT" / "stimuli" / "refined_cdm_cat"
       / "stimulus_master_cdm_cat_v3.csv").resolve()
TARGET_AUDIO_DIR = SCRIPT_DIR / "audio_grammaticality" / "target"
PRIME_AUDIO_DIR = SCRIPT_DIR / "audio_grammaticality" / "prime"
ALIGNMENT_OUT = SCRIPT_DIR / "alignments"


# =========================================================
# Backend: whisperX
# =========================================================

def align_with_whisperx(audio_path, text, language="en"):
    """Use whisperX for word-level alignment.

    Returns list of {"word": str, "start": float, "end": float} dicts.
    """
    try:
        import whisperx
    except ImportError:
        raise SystemExit(
            "whisperx not installed. Run: pip install whisperx"
        )
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    # Load alignment model (cached on subsequent calls)
    model_a, metadata = whisperx.load_align_model(
        language_code=language, device=device
    )
    audio = whisperx.load_audio(str(audio_path))

    # Build a fake transcript segment for alignment
    segments = [{
        "start": 0.0,
        "end": len(audio) / 16000.0,
        "text": text,
    }]
    aligned = whisperx.align(
        segments, model_a, metadata, audio, device,
        return_char_alignments=False,
    )
    words = []
    for seg in aligned["segments"]:
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w.get("start"),
                "end": w.get("end"),
            })
    return words


# =========================================================
# Backend: Gentle
# =========================================================

def align_with_gentle(audio_path, text):
    """Use Gentle Docker container for alignment.

    Requires: docker pull lowerquality/gentle
    Returns list of {"word", "start", "end"} dicts.
    """
    # Write transcript to temp file
    transcript_path = audio_path.with_suffix(".txt")
    transcript_path.write_text(text)
    cmd = [
        "docker", "run", "-v", f"{audio_path.parent.absolute()}:/data",
        "lowerquality/gentle", "/gentle/align.py",
        f"/data/{audio_path.name}", f"/data/{transcript_path.name}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Gentle failed: {result.stderr}")
    j = json.loads(result.stdout)
    return [
        {"word": w["word"], "start": w.get("start"), "end": w.get("end")}
        for w in j.get("words", [])
    ]


# =========================================================
# Backend: pre-computed JSON
# =========================================================

def align_from_json(audio_path, json_dir):
    """Load pre-computed alignment from JSON file."""
    json_file = Path(json_dir) / f"{audio_path.stem}.json"
    if not json_file.exists():
        return None
    data = json.loads(json_file.read_text())
    return data if isinstance(data, list) else data.get("words", [])


# =========================================================
# Critical word extraction
# =========================================================

def find_critical_onset(alignment, critical_region_text):
    """Find onset time (ms) of first word in critical_region_text.

    Returns (onset_ms, duration_ms) tuple. None if not found.
    """
    if not critical_region_text or not alignment:
        return None, None

    # Tokenize critical region
    crit_words = re.findall(r"\b\w+\b", critical_region_text.lower())
    if not crit_words:
        return None, None
    first_crit = crit_words[0]

    # Find first occurrence in alignment
    for i, w in enumerate(alignment):
        word_clean = re.sub(r"[^\w]", "", w.get("word", "").lower())
        if word_clean == first_crit:
            start = w.get("start")
            # Find end of last critical word
            end = w.get("end")
            for cw_idx in range(1, len(crit_words)):
                if i + cw_idx < len(alignment):
                    next_w = alignment[i + cw_idx]
                    next_clean = re.sub(r"[^\w]", "", next_w.get("word", "").lower())
                    if next_clean == crit_words[cw_idx]:
                        end = next_w.get("end")
            if start is not None and end is not None:
                return start * 1000, (end - start) * 1000
            return None, None
    return None, None


# =========================================================
# Main
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend", choices=["whisperx", "gentle", "json"], default="whisperx",
    )
    parser.add_argument("--json-dir", default=str(ALIGNMENT_OUT),
                        help="Directory with pre-computed alignment JSON files.")
    parser.add_argument("--items", default=None,
                        help="Comma-separated item_id list (subset).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print alignments without updating CSV.")
    parser.add_argument("--out-csv", default=None,
                        help="Output CSV path (default: overwrite master).")
    args = parser.parse_args()

    if not CSV.exists():
        print(f"Master CSV not found: {CSV}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV, dtype={"q_vector": str})
    item_filter = set(args.items.split(",")) if args.items else None

    # Add columns if missing
    if "critical_word_onset_ms_aligned" not in df.columns:
        df["critical_word_onset_ms_aligned"] = None
    if "critical_word_duration_ms_aligned" not in df.columns:
        df["critical_word_duration_ms_aligned"] = None

    n_processed = 0
    n_aligned = 0
    n_skipped = 0
    n_missing_audio = 0

    for idx, row in df.iterrows():
        item_id = row["item_id"]
        if item_filter and item_id not in item_filter:
            continue
        if row.get("item_type") != "critical":
            n_skipped += 1
            continue

        audio_path = TARGET_AUDIO_DIR / f"{item_id}.wav"
        if not audio_path.exists():
            audio_path_mp3 = TARGET_AUDIO_DIR / f"{item_id}.mp3"
            if audio_path_mp3.exists():
                audio_path = audio_path_mp3
            else:
                n_missing_audio += 1
                continue

        text = row["target_text"]
        critical_region = row.get("critical_region", "")

        n_processed += 1

        try:
            if args.backend == "whisperx":
                alignment = align_with_whisperx(audio_path, text)
            elif args.backend == "gentle":
                alignment = align_with_gentle(audio_path, text)
            else:
                alignment = align_from_json(audio_path, args.json_dir)
                if alignment is None:
                    n_missing_audio += 1
                    continue
        except Exception as e:
            print(f"  [{item_id}] alignment error: {e}")
            continue

        onset_ms, duration_ms = find_critical_onset(alignment, critical_region)
        if onset_ms is not None:
            n_aligned += 1
            df.at[idx, "critical_word_onset_ms_aligned"] = round(onset_ms, 1)
            df.at[idx, "critical_word_duration_ms_aligned"] = round(duration_ms, 1)
            print(f"  [{item_id}] critical='{critical_region}' onset={onset_ms:.1f}ms dur={duration_ms:.1f}ms")
        else:
            print(f"  [{item_id}] critical region not found in alignment")

    print(f"\nProcessed: {n_processed}, Aligned: {n_aligned}, "
          f"Skipped: {n_skipped}, Missing audio: {n_missing_audio}")

    if args.dry_run:
        print("Dry-run: not saving CSV.")
        return

    out_path = Path(args.out_csv) if args.out_csv else CSV
    df.to_csv(out_path, index=False)
    print(f"Updated CSV: {out_path}")


if __name__ == "__main__":
    main()
