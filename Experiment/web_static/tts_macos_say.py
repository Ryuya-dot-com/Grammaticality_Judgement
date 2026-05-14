#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
macOS `say` based TTS Generation (no API keys required)

Generates all 348 audio files (132 primes + 216 targets) using macOS's
built-in `say` command. Output quality is acceptable for behavioral pilots
and development testing; for production fMRI use Amazon Polly Neural
(see ../fMRI/tts_generate_audio.py).

Usage:
    # Generate all (may take 10-20 min)
    python3 tts_macos_say.py

    # Specific subset
    python3 tts_macos_say.py --items P007U,P008U
    python3 tts_macos_say.py --only-primes
    python3 tts_macos_say.py --only-targets

    # Different voice (default: Samantha)
    python3 tts_macos_say.py --voice Alex

Voices available (macOS): Samantha, Alex, Daniel, Karen, Moira, Tessa, ...
List voices with: `say -v ?`

For F02 U items (a + vowel), the script inserts a brief pause + phonetic
hint to encourage schwa pronunciation. Manual QA is still recommended.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
STIMULI_JSON = SCRIPT_DIR / "stimuli.json"
PRIME_DIR = SCRIPT_DIR / "audio" / "prime"
TARGET_DIR = SCRIPT_DIR / "audio" / "target"


def make_say_input_with_aan_override(text):
    """For F02 U items: force '/ə/' on 'a' before vowel-initial noun.

    macOS `say` doesn't support full SSML, but accepts phonetic input via
    [[inpt PHON]] mode. We use a simpler approach: insert a small pause
    and use [[slnc 100]] to prevent coarticulation.
    """
    pattern = re.compile(r"\ba(\s+)([aeiouAEIOU]\w+)")
    def repl(m):
        return f"uh [[slnc 100]]{m.group(1)}{m.group(2)}"
    return pattern.sub(repl, text)


def say_to_aiff(text, output_aiff, voice="Samantha", rate=160):
    """Generate AIFF via macOS `say`."""
    cmd = ["say", "-v", voice, "-r", str(rate), "-o", str(output_aiff), text]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"say failed: {result.stderr}")


def aiff_to_wav(aiff_path, wav_path):
    """Convert AIFF to 44.1kHz mono WAV via afconvert (built-in on macOS)."""
    cmd = [
        "afconvert", "-f", "WAVE", "-d", "LEI16@44100",
        "-c", "1", str(aiff_path), str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"afconvert failed: {result.stderr}")


def get_tasks(items, only_primes=False, only_targets=False, item_filter=None):
    """Build list of (text, out_path, is_f02_u, is_f01_u, label) tasks."""
    tasks = []
    primes_done = set()
    if not only_targets:
        for it in items:
            pid = it.get("pair_id")
            iid = it.get("item_id")
            key = pid if it.get("item_type") == "critical" else iid
            if key in primes_done:
                continue
            primes_done.add(key)
            if item_filter and iid not in item_filter:
                continue
            tasks.append({
                "text": it["prime_text"],
                "out": PRIME_DIR / f"{key}.wav",
                "is_f02_u": False,
                "is_f01_u": False,
                "label": f"prime/{key}",
            })

    if not only_primes:
        for it in items:
            iid = it["item_id"]
            if item_filter and iid not in item_filter:
                continue
            is_f02_u = (it.get("family_id") == "F02" and it.get("version") == "U")
            is_f01_u = (it.get("family_id") == "F01" and it.get("version") == "U")
            tasks.append({
                "text": it["target_text"],
                "out": TARGET_DIR / f"{iid}.wav",
                "is_f02_u": is_f02_u,
                "is_f01_u": is_f01_u,
                "label": f"target/{iid}",
            })
    return tasks


def pad_f01_u_silence(wav_path, silence_ms=370):
    """Append silence to F01 U audio. Returns True on success."""
    try:
        import wave
        with wave.open(str(wav_path), "rb") as w:
            params = w.getparams()
            frames = w.readframes(w.getnframes())
        n_silence = int(params.framerate * silence_ms / 1000)
        sample_width = params.sampwidth
        nchannels = params.nchannels
        silence = b"\x00" * (n_silence * sample_width * nchannels)
        with wave.open(str(wav_path), "wb") as w:
            w.setparams(params)
            w.writeframes(frames + silence)
        return True
    except Exception as e:
        print(f"  silence padding failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="Samantha",
                        help="macOS voice name (default: Samantha; list with `say -v ?`)")
    parser.add_argument("--rate", type=int, default=160,
                        help="Speech rate in words/min (default: 160)")
    parser.add_argument("--only-primes", action="store_true")
    parser.add_argument("--only-targets", action="store_true")
    parser.add_argument("--items", default=None,
                        help="Comma-separated item_id list (e.g., P007U,P008U)")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    parser.add_argument("--pad-f01-u", action="store_true", default=False,
                        help="Add 370ms trailing silence to F01 U files. "
                             "Only needed for fast TTS engines like Polly Neural. "
                             "macOS `say` does NOT need this (default: off).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if sys.platform != "darwin":
        print("This script requires macOS (uses `say` and `afconvert`).", file=sys.stderr)
        sys.exit(1)

    if not STIMULI_JSON.exists():
        print(f"stimuli.json not found at {STIMULI_JSON}", file=sys.stderr)
        print("Run convert_csv_to_json.py first.")
        sys.exit(1)

    PRIME_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    items = json.loads(STIMULI_JSON.read_text())
    item_filter = set(args.items.split(",")) if args.items else None

    tasks = get_tasks(items, args.only_primes, args.only_targets, item_filter)
    print(f"Total tasks: {len(tasks)} (voice={args.voice}, rate={args.rate})")

    if args.dry_run:
        print("\nDry-run preview (first 8):")
        for t in tasks[:8]:
            flags = []
            if t["is_f02_u"]: flags.append("F02-SSML")
            if t["is_f01_u"]: flags.append("F01-pad")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            print(f"  {t['label']}: {t['text']!r}{flag_str}")
        print(f"  ... ({len(tasks) - 8} more)")
        return

    n_done = n_skip = n_err = 0
    for i, task in enumerate(tasks, 1):
        out = task["out"]
        if args.skip_existing and out.exists():
            n_skip += 1
            continue

        text = task["text"]
        if task["is_f02_u"]:
            text = make_say_input_with_aan_override(text)

        aiff_tmp = out.with_suffix(".aiff")
        try:
            say_to_aiff(text, aiff_tmp, voice=args.voice, rate=args.rate)
            aiff_to_wav(aiff_tmp, out)
            aiff_tmp.unlink(missing_ok=True)
            if task["is_f01_u"] and args.pad_f01_u:
                pad_f01_u_silence(out, silence_ms=370)
            n_done += 1
            print(f"[{i:3d}/{len(tasks)}] OK  {task['label']}")
        except Exception as e:
            n_err += 1
            print(f"[{i:3d}/{len(tasks)}] ERR {task['label']}: {e}")

        # Tiny throttle
        if i % 20 == 0:
            time.sleep(0.1)

    print(f"\nDone: {n_done} generated, {n_skip} skipped, {n_err} errors")
    print(f"\nF02 U items (manual QA recommended — confirm 'a + vowel' is not auto-coarticulated):")
    for it in items:
        if it.get("family_id") == "F02" and it.get("version") == "U":
            wav = TARGET_DIR / f"{it['item_id']}.wav"
            print(f"  {it['item_id']}: '{it['target_text']}'  →  {wav}")


if __name__ == "__main__":
    main()
