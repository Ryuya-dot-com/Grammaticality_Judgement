#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TTS Audio Generation Helper for Grammaticality_RWL_fMRI.py

Generates 132 prime + 216 target audio files using Amazon Polly Neural
(preferred, supports SSML for F02 a/an override) or OpenAI tts-1.

Usage:
    # Amazon Polly (recommended)
    export AWS_ACCESS_KEY_ID="..."
    export AWS_SECRET_ACCESS_KEY="..."
    export AWS_DEFAULT_REGION="ap-northeast-1"
    python3 tts_generate_audio.py --service polly --voice Joanna

    # OpenAI TTS
    export OPENAI_API_KEY="..."
    python3 tts_generate_audio.py --service openai --voice nova

    # Specific subset
    python3 tts_generate_audio.py --service polly --voice Joanna --only-targets
    python3 tts_generate_audio.py --service polly --voice Joanna --items P007U,P008U  # only F02 U items
"""

import argparse
import os
import re
import sys
import time

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STIMULUS_CSV = os.path.join(
    SCRIPT_DIR, "..", "..",
    "Grammaticality_Judgement_CAT", "stimuli", "refined_cdm_cat",
    "stimulus_master_cdm_cat_v3.csv",
)

PRIME_DIR = os.path.join(SCRIPT_DIR, "audio_grammaticality", "prime")
TARGET_DIR = os.path.join(SCRIPT_DIR, "audio_grammaticality", "target")


# =========================================================
# SSML helpers (Polly only)
# =========================================================

def make_ssml_with_aan_override(text):
    """For F02 U items: force '/ə/' pronunciation of 'a' before vowel-initial noun."""
    pattern = re.compile(r"\ba(\s+)([aeiouAEIOU]\w+)")
    def repl(m):
        return (f'<phoneme alphabet="ipa" ph="ə">a</phoneme>'
                f'<break time="80ms"/>{m.group(1)}{m.group(2)}')
    return f"<speak>{pattern.sub(repl, text)}</speak>"


def make_ssml_standard(text):
    """Standard SSML wrapper."""
    return f"<speak>{text}</speak>"


# =========================================================
# Polly
# =========================================================

def synth_polly(text, output_path, voice="Joanna", use_ssml=False):
    """Call Amazon Polly Neural and save MP3."""
    import boto3
    client = boto3.client("polly")
    kwargs = {
        "VoiceId": voice,
        "Engine": "neural",
        "OutputFormat": "mp3",
    }
    if use_ssml:
        kwargs["Text"] = text
        kwargs["TextType"] = "ssml"
    else:
        kwargs["Text"] = text
        kwargs["TextType"] = "text"
    resp = client.synthesize_speech(**kwargs)
    audio_bytes = resp["AudioStream"].read()
    with open(output_path, "wb") as f:
        f.write(audio_bytes)


# =========================================================
# OpenAI
# =========================================================

def synth_openai(text, output_path, voice="nova"):
    """Call OpenAI tts-1 and save MP3."""
    from openai import OpenAI
    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
    )
    response.stream_to_file(output_path)


# =========================================================
# Convert MP3 → WAV (optional but recommended for pygame)
# =========================================================

def mp3_to_wav(mp3_path, wav_path):
    """Use ffmpeg to convert MP3 to WAV. Returns True on success."""
    import subprocess
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  ffmpeg conversion failed: {e}")
        return False


# =========================================================
# F01 U silence padding (post-generation)
# =========================================================

def pad_f01_u_trailing_silence(wav_path, silence_ms=370):
    """Pad F01 U audio with trailing silence to equate length with G."""
    try:
        import wave, struct
        with wave.open(wav_path, "rb") as wav_in:
            params = wav_in.getparams()
            frames = wav_in.readframes(wav_in.getnframes())
        n_silence_frames = int(params.framerate * silence_ms / 1000)
        sample_width = params.sampwidth
        silence_bytes = b"\x00" * (n_silence_frames * sample_width * params.nchannels)
        padded = frames + silence_bytes
        with wave.open(wav_path, "wb") as wav_out:
            wav_out.setparams(params)
            wav_out.writeframes(padded)
        return True
    except Exception as e:
        print(f"  Silence padding failed for {wav_path}: {e}")
        return False


# =========================================================
# Audio task list builders
# =========================================================

def get_audio_tasks(df, only_primes=False, only_targets=False, item_filter=None):
    """Build list of (text, output_path, use_ssml, is_f01_u) tuples."""
    tasks = []
    # Primes (one per pair_id for critical; per item_id for fillers)
    if not only_targets:
        primes_done = set()
        for _, row in df.iterrows():
            pid = row["pair_id"]
            if row["item_type"] == "critical":
                key = pid
            else:
                key = row["item_id"]
            if key in primes_done:
                continue
            primes_done.add(key)
            if item_filter and row["item_id"] not in item_filter:
                continue
            out_path = os.path.join(PRIME_DIR, f"{key}.wav")
            tasks.append({
                "text": row["prime_text"],
                "out": out_path,
                "use_ssml": False,
                "is_f01_u": False,
                "label": f"prime/{key}",
            })

    # Targets (per item_id)
    if not only_primes:
        for _, row in df.iterrows():
            iid = row["item_id"]
            if item_filter and iid not in item_filter:
                continue
            out_path = os.path.join(TARGET_DIR, f"{iid}.wav")
            use_ssml = (row.get("family_id") == "F02" and row.get("version") == "U")
            is_f01_u = (row.get("family_id") == "F01" and row.get("version") == "U")
            tasks.append({
                "text": row["target_text"],
                "out": out_path,
                "use_ssml": use_ssml,
                "is_f01_u": is_f01_u,
                "label": f"target/{iid}",
            })
    return tasks


# =========================================================
# Main
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=["polly", "openai"], default="polly")
    parser.add_argument("--voice", default="Joanna")
    parser.add_argument("--only-primes", action="store_true")
    parser.add_argument("--only-targets", action="store_true")
    parser.add_argument("--items", default=None,
                        help="Comma-separated item_id list (e.g., P007U,P008U)")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(STIMULUS_CSV):
        print(f"Stimulus CSV not found: {STIMULUS_CSV}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(PRIME_DIR, exist_ok=True)
    os.makedirs(TARGET_DIR, exist_ok=True)

    df = pd.read_csv(STIMULUS_CSV, dtype={"q_vector": str})
    item_filter = set(args.items.split(",")) if args.items else None

    tasks = get_audio_tasks(
        df,
        only_primes=args.only_primes,
        only_targets=args.only_targets,
        item_filter=item_filter,
    )
    print(f"Total tasks: {len(tasks)}")
    if args.dry_run:
        for t in tasks[:5]:
            ssml_flag = " [SSML]" if t["use_ssml"] else ""
            f01_flag = " [F01-pad]" if t["is_f01_u"] else ""
            print(f"  {t['label']}: '{t['text']}'{ssml_flag}{f01_flag}")
        print(f"  ... ({len(tasks)-5} more)")
        return

    # Generate
    for i, task in enumerate(tasks, 1):
        out = task["out"]
        if args.skip_existing and os.path.exists(out):
            print(f"[{i:3d}/{len(tasks)}] SKIP (exists): {task['label']}")
            continue
        text = task["text"]
        use_ssml = task["use_ssml"]
        if use_ssml:
            text = make_ssml_with_aan_override(task["text"])

        # Synthesize to a temporary mp3, then convert to wav
        mp3_out = out.replace(".wav", ".mp3")
        print(f"[{i:3d}/{len(tasks)}] {task['label']} ({'SSML' if use_ssml else 'plain'})")
        try:
            if args.service == "polly":
                synth_polly(text, mp3_out, voice=args.voice, use_ssml=use_ssml)
            else:
                synth_openai(task["text"], mp3_out, voice=args.voice)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue

        # Convert to wav for pygame compatibility
        if mp3_to_wav(mp3_out, out):
            os.remove(mp3_out)
        else:
            # Keep mp3 if conversion failed (pygame supports both)
            os.rename(mp3_out, out.replace(".wav", ".mp3"))
            print(f"  Saved as .mp3 (ffmpeg unavailable)")

        # F01 U trailing silence
        if task["is_f01_u"] and out.endswith(".wav"):
            if pad_f01_u_trailing_silence(out, silence_ms=370):
                print(f"  Padded 370 ms trailing silence")

        # Rate limit (Polly 100 req/s but stay polite)
        time.sleep(0.1)

    print("\nDone. Verify F02 U items manually:")
    for _, row in df[(df["family_id"] == "F02") & (df["version"] == "U")].iterrows():
        wav = os.path.join(TARGET_DIR, f"{row['item_id']}.wav")
        mp3 = os.path.join(TARGET_DIR, f"{row['item_id']}.mp3")
        path = wav if os.path.exists(wav) else mp3
        print(f"  {row['item_id']}: {row['target_text']}  →  {path}")


if __name__ == "__main__":
    main()
