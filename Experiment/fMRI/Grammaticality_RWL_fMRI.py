#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grammaticality Judgment Task (Pygame, RWL fMRI Version)

Reading-While-Listening (RWL) grammaticality-judgment task for L1 Japanese
B1-B2 English learners. Each trial presents a prime (text + audio) and a
target (text + audio) with 2AFC grammaticality judgment.

Stimulus source: stimulus_master_cdm_cat_v3.csv
Audio source: audio_grammaticality/{prime,target}/*.wav (or .mp3)

Design:
- 84 critical pairs (14 word families × 6 pairs) + 48 fillers = 132 items/form
- Latin square: Form A or Form B (counterbalanced across participants)
- 4 runs × ~33 trials × ~8 sec/trial = ~22 min total
- Each trial: fixation (500ms) → prime (text+audio, ~3500ms)
  → pause (500ms) → target (text+audio + response, ~3500ms) → ITI (500-2500ms)

Response keys:
- 1 = "Grammatical in this context"
- 2 = "Not grammatical in this context"
- 5 = fMRI trigger / continue
- Esc = abort (saves data)
- Cmd+Shift+Esc = pause / resume

Usage:
    python Grammaticality_RWL_fMRI.py
"""

import pygame
from pygame.locals import *
import os
import sys
import csv
import random
import logging
import time
import unicodedata
from datetime import datetime

import pandas as pd
import numpy as np

# =========================================================
# Constants / configuration
# =========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Stimulus and audio paths (relative to this script)
STIMULUS_CSV = os.path.join(
    SCRIPT_DIR,
    "..",
    "..",
    "Grammaticality_Judgement_CAT",
    "stimuli",
    "refined_cdm_cat",
    "stimulus_master_cdm_cat_v3.csv",
)
AUDIO_DIR = os.path.join(SCRIPT_DIR, "audio_grammaticality")
PRIME_AUDIO_DIR = os.path.join(AUDIO_DIR, "prime")
TARGET_AUDIO_DIR = os.path.join(AUDIO_DIR, "target")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results_grammaticality")

# Trial timing (ms)
FIXATION_MS = 500
PRIME_MAX_MS = 3500
PAUSE_MS = 500
TARGET_MAX_MS = 2500
RESPONSE_WINDOW_MS = 2000
ITI_MIN_MS = 500
ITI_MAX_MS = 2500

# Run structure
INITIAL_REST_MS = 10000
INTER_RUN_REST_MS = 30000
FINAL_REST_MS = 10000

# Display
TEXT_FONT_SIZE = 48
FIXATION_FONT_SIZE = 72
INSTRUCTION_FONT_SIZE = 36

# Colors (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 60, 60)
GRAY = (160, 160, 160)

# Response key normalization
NUMERIC_KEY_MAP = {
    K_0: ("0", "number_row"), K_1: ("1", "number_row"), K_2: ("2", "number_row"),
    K_3: ("3", "number_row"), K_4: ("4", "number_row"), K_5: ("5", "number_row"),
    K_6: ("6", "number_row"), K_7: ("7", "number_row"), K_8: ("8", "number_row"),
    K_9: ("9", "number_row"),
    K_KP0: ("0", "numpad"), K_KP1: ("1", "numpad"), K_KP2: ("2", "numpad"),
    K_KP3: ("3", "numpad"), K_KP4: ("4", "numpad"), K_KP5: ("5", "numpad"),
    K_KP6: ("6", "numpad"), K_KP7: ("7", "numpad"), K_KP8: ("8", "numpad"),
    K_KP9: ("9", "numpad"),
}

# CSV columns to save in results
RESULT_COLUMNS = [
    "run", "trial", "item_id", "pair_id", "version", "item_type",
    "family_id", "construct", "q_vector",
    "prime_text", "target_text", "target_lemma", "critical_region",
    "expected_response", "response", "response_correct",
    "rt_from_target_onset_ms", "rt_from_critical_onset_ms",
    "response_key_name", "response_key_source",
    "prime_audio_onset_ms", "prime_audio_duration_ms",
    "target_audio_onset_ms", "target_audio_duration_ms",
    "iti_ms", "time", "onset_from_trigger_s", "list_form",
]

KEY_EVENT_COLUMNS = [
    "Participant", "date", "session_timestamp", "run", "trial",
    "item_id", "phase", "key_code", "key_name", "key_label", "key_source",
    "normalized_response", "phase_time_ms", "time", "onset_from_trigger_s",
]

# Globals
script_clock_start_ms = None
first_trigger_time_ms = None
experiment_paused = False
pause_start_time_ms = None
jp_font_path = None
default_jp_font_name = None


# =========================================================
# Custom exceptions
# =========================================================

class ExperimentAbortRequested(Exception):
    """Allow safe save-and-exit on Esc or close."""
    pass


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def log(msg):
    """Print + log message with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}")
    logging.info(msg)


# =========================================================
# High-precision timing
# =========================================================

def get_time_ms():
    """Return high-precision monotonic time in milliseconds."""
    return time.perf_counter() * 1000


def onset_from_trigger_s(now_ms=None):
    """Seconds since fMRI trigger."""
    if first_trigger_time_ms is None:
        return None
    if now_ms is None:
        now_ms = get_time_ms()
    return (now_ms - first_trigger_time_ms) / 1000.0


# =========================================================
# Key handling
# =========================================================

def normalize_response_key(key_code):
    """Normalize response keys for analysis. Returns '1', '2', or None."""
    if key_code in (K_1, K_KP1):
        return "1"
    if key_code in (K_2, K_KP2):
        return "2"
    return None


def get_key_metadata(key_code):
    """Return (key_name, label, source) tuple."""
    key_name = pygame.key.name(key_code)
    if key_code in NUMERIC_KEY_MAP:
        label, source = NUMERIC_KEY_MAP[key_code]
        return key_name, label, source
    return key_name, key_name, "other"


def log_key_event(key_events, run, trial, item_id, phase,
                  phase_start_ms, key_code):
    """Append a key-press event to the event log."""
    now_ms = get_time_ms()
    key_name, key_label, key_source = get_key_metadata(key_code)
    key_events.append({
        "run": run, "trial": trial, "item_id": item_id, "phase": phase,
        "key_code": key_code, "key_name": key_name, "key_label": key_label,
        "key_source": key_source,
        "normalized_response": normalize_response_key(key_code),
        "phase_time_ms": (now_ms - phase_start_ms) if phase_start_ms else None,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "onset_from_trigger_s": onset_from_trigger_s(now_ms),
    })
    return now_ms, key_name, key_label, key_source


# =========================================================
# Pause / resume
# =========================================================

def check_pause():
    """Return True if Cmd+Shift+Esc is held (start pause)."""
    global experiment_paused, pause_start_time_ms
    keys = pygame.key.get_pressed()
    if (keys[K_LMETA] or keys[K_RMETA]) and keys[K_LSHIFT] and keys[K_ESCAPE]:
        if not experiment_paused:
            experiment_paused = True
            pause_start_time_ms = get_time_ms()
            log("Pause initiated.")
            return True
    return False


def handle_pause(screen):
    """Handle pause state: display message, wait for resume keys."""
    global experiment_paused, pause_start_time_ms
    if not experiment_paused:
        return 0
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()

    screen.fill(BLACK)
    display_text(screen,
                 "一時停止中...\n\nCommand+Shift+Esc で再開",
                 font_size=40)
    pause_duration = 0
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("pause_screen_closed")
        keys = pygame.key.get_pressed()
        if (keys[K_LMETA] or keys[K_RMETA]) and keys[K_LSHIFT] and keys[K_ESCAPE]:
            if experiment_paused:
                experiment_paused = False
                screen.fill(BLACK)
                pygame.display.flip()
                pygame.mouse.set_visible(False)
                pygame.mixer.music.unpause()
                waiting = False
                pygame.time.wait(500)
                pause_duration = get_time_ms() - pause_start_time_ms
                log(f"Resumed. Pause duration: {pause_duration:.1f} ms")
        pygame.time.wait(50)
    return pause_duration


# =========================================================
# Font setup
# =========================================================

def setup_fonts():
    """Locate Japanese font for instruction screens."""
    global jp_font_path, default_jp_font_name
    candidate = os.path.join(SCRIPT_DIR, "fonts", "static", "NotoSansJP-Regular.ttf")
    if os.path.exists(candidate):
        jp_font_path = candidate
        log(f"JP font found: {jp_font_path}")
    else:
        log(f"JP font not found at {candidate}; will use system font.")
    if sys.platform.startswith("darwin"):
        default_jp_font_name = "Hiragino Sans"
    elif sys.platform.startswith("win"):
        default_jp_font_name = "Yu Gothic"
    else:
        default_jp_font_name = "Noto Sans CJK JP"


def get_font(size, jp_friendly=True):
    """Return pygame Font object for size; prefer NotoSansJP if available."""
    if jp_friendly and jp_font_path and os.path.exists(jp_font_path):
        return pygame.font.Font(jp_font_path, size)
    if jp_friendly:
        try:
            return pygame.font.SysFont(default_jp_font_name, size)
        except Exception:
            return pygame.font.Font(None, size)
    return pygame.font.Font(None, size)


# =========================================================
# Display helpers
# =========================================================

def display_text(screen, text, font_size=TEXT_FONT_SIZE,
                 color=WHITE, y_offset=0, line_spacing=1.3,
                 jp_friendly=True, clear=True):
    """Display centered text. Newlines split lines."""
    if clear:
        screen.fill(BLACK)
    font = get_font(font_size, jp_friendly=jp_friendly)
    lines = text.split("\n")
    sw, sh = screen.get_size()
    rendered = []
    for ln in lines:
        if ln.strip():
            surf = font.render(ln.strip(), True, color)
            rendered.append(surf)
        else:
            rendered.append(None)
    line_h = font.get_height()
    total_h = len(rendered) * line_h * line_spacing
    start_y = (sh - total_h) // 2 + y_offset
    y = start_y
    for surf in rendered:
        if surf is not None:
            rect = surf.get_rect(centerx=sw // 2,
                                 centery=int(y + line_h // 2))
            screen.blit(surf, rect)
        y += line_h * line_spacing
    pygame.display.flip()


def display_fixation(screen, duration_ms, run=0, trial=0,
                     phase="fixation", key_events=None):
    """Display fixation cross for duration_ms (with pause check + Esc)."""
    font = get_font(FIXATION_FONT_SIZE, jp_friendly=False)
    surf = font.render("+", True, WHITE)
    sw, sh = screen.get_size()
    rect = surf.get_rect(center=(sw // 2, sh // 2))

    screen.fill(BLACK)
    screen.blit(surf, rect)
    pygame.display.flip()

    start_ms = get_time_ms()
    while get_time_ms() - start_ms < duration_ms:
        if check_pause():
            pause_duration = handle_pause(screen)
            start_ms += pause_duration
            screen.fill(BLACK)
            screen.blit(surf, rect)
            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_during_fixation")
            if event.type == KEYDOWN:
                if key_events is not None:
                    log_key_event(key_events, run, trial, "FIXATION",
                                  phase, start_ms, event.key)
                if event.key == K_ESCAPE:
                    raise ExperimentAbortRequested("escape_during_fixation")
        pygame.time.wait(1)


# =========================================================
# Audio helpers
# =========================================================

def get_audio_path(item_id, pair_id, kind):
    """Return path to audio file (.wav preferred, fall back to .mp3).

    For primes: critical items share prime per pair_id; fillers use item_id.
    For targets: use item_id.
    """
    if kind == "prime":
        # Critical pair shares prime; filler uses item_id which equals pair_id
        stem = pair_id
        base_dir = PRIME_AUDIO_DIR
    else:  # target
        stem = item_id
        base_dir = TARGET_AUDIO_DIR

    for ext in (".wav", ".mp3"):
        path = os.path.join(base_dir, stem + ext)
        if os.path.exists(path):
            return path
    return None


def play_audio_blocking(audio_path, max_wait_ms):
    """Start audio playback. Returns (start_ms, duration_ms).

    Does NOT block — returns immediately so caller can run response loop.
    The caller can check pygame.mixer.music.get_busy() to know when done.
    """
    if audio_path is None or not os.path.exists(audio_path):
        return None, None
    try:
        snd = pygame.mixer.Sound(audio_path)
        duration_ms = int(snd.get_length() * 1000)
        # Use channel-based playback to avoid music.load overhead
        channel = pygame.mixer.find_channel(force=True)
        start_ms = get_time_ms()
        channel.play(snd)
        return start_ms, duration_ms
    except Exception as exc:
        log(f"Audio play error for {audio_path}: {exc}")
        return None, None


# =========================================================
# CSV loading + form filtering
# =========================================================

def load_stimuli(csv_path, list_form):
    """Load master CSV and return items for the given form (A or B).

    Returns a list of dicts in trial order (run × trial_index).
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Stimulus CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype={"q_vector": str})
    # Items for this form: list_form == form OR list_form == 'AB' (fillers)
    sub = df[df["list_form"].isin([list_form, "AB"])].copy()
    # Get run_assignment column for this form
    run_col = f"run_assignment_{list_form}"
    trial_col = f"trial_index_{list_form}"
    if run_col not in sub.columns or trial_col not in sub.columns:
        raise KeyError(f"Required columns {run_col} / {trial_col} missing.")
    sub = sub.dropna(subset=[run_col, trial_col]).copy()
    sub["run_int"] = sub[run_col].astype(int)
    sub["trial_int"] = sub[trial_col].astype(int)
    sub = sub.sort_values(["run_int", "trial_int"]).reset_index(drop=True)

    items = sub.to_dict(orient="records")
    log(f"Loaded {len(items)} items for Form {list_form}")
    return items


def split_by_run(items):
    """Group items into 4 runs based on run_int."""
    runs = {1: [], 2: [], 3: [], 4: []}
    for it in items:
        runs[it["run_int"]].append(it)
    return runs


# =========================================================
# Screen setup
# =========================================================

def setup_screen():
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    log(f"Screen resolution: {sw}x{sh}")
    screen = pygame.display.set_mode((sw, sh), FULLSCREEN | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    pygame.display.set_caption("Grammaticality Judgment (RWL fMRI)")
    return screen


# =========================================================
# Participant info dialog
# =========================================================

def get_participant_info():
    """Collect participant ID + Latin-square form from CLI."""
    print("\n=== Grammaticality Judgment Task (RWL fMRI) ===\n")
    exp_info = {
        "Participant": "",
        "list_form": "",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        pid = input("Participant ID (例: 001): ").strip()
        if not pid:
            pid = datetime.now().strftime("%Y%m%d%H%M%S")
            print(f"  → defaulting to {pid}")
        exp_info["Participant"] = pid

        # Form A or B
        form = ""
        while form not in ("A", "B"):
            form = input("Latin-square Form [A/B]: ").strip().upper()
            if form not in ("A", "B"):
                # Auto-assign based on participant ID parity
                try:
                    pid_int = int(pid)
                    form = "A" if pid_int % 2 == 1 else "B"
                    print(f"  → auto-assigned Form {form} (parity rule)")
                    break
                except ValueError:
                    print("  Please enter A or B.")
        exp_info["list_form"] = form
    except Exception as exc:
        print(f"Input error: {exc}; using defaults.")
        exp_info["Participant"] = datetime.now().strftime("%Y%m%d%H%M%S")
        exp_info["list_form"] = "A"

    print("\nSession info:")
    print(f"  Participant: {exp_info['Participant']}")
    print(f"  Form: {exp_info['list_form']}")
    print(f"  Date: {exp_info['date']}")
    print("\nStarting experiment...\n")
    return exp_info


# =========================================================
# Instructions
# =========================================================

INSTRUCTION_TEXT = """これから、文と音声が画面と耳に同時に提示されます。

1つの試行は次のように進みます:
  (1) 場面を説明する文
  (2) 短い間
  (3) 判断対象の文

判断対象の文がその場面で「文法的に正しい」場合は
人差し指のボタン (1) を押してください。

「文法的に正しくない」場合は
中指のボタン (2) を押してください。

できるだけ早く正確にボタンを押してください。
1回約8秒の試行で、4回のランがあります。

(準備ができたら 5 キーまたはトリガーで開始)"""


def show_instructions(screen):
    """Show instructions and wait for trigger '5' or Esc."""
    display_text(screen, INSTRUCTION_TEXT, font_size=INSTRUCTION_FONT_SIZE)
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_on_instructions")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_5:
                    waiting = False
    screen.fill(BLACK)
    pygame.display.flip()
    return True


def wait_for_trigger(screen, key_events, run_label="run1"):
    """Wait for fMRI trigger ('5'). Sets first_trigger_time_ms on receipt."""
    global first_trigger_time_ms
    display_text(screen, "しばらくお待ちください...", font_size=40)
    log(f"Waiting for trigger ({run_label})")
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_waiting_trigger")
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_5:
                    first_trigger_time_ms = get_time_ms()
                    log(f"Trigger received at {first_trigger_time_ms:.1f} ms")
                    key_events.append({
                        "run": 0, "trial": 0, "item_id": "TRIGGER",
                        "phase": run_label, "key_code": K_5,
                        "key_name": "5", "key_label": "5",
                        "key_source": "number_row",
                        "normalized_response": None,
                        "phase_time_ms": 0.0,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "onset_from_trigger_s": 0.0,
                    })
                    waiting = False
    screen.fill(BLACK)
    pygame.display.flip()
    pygame.event.clear()
    return True


# =========================================================
# Trial execution
# =========================================================

def run_trial(screen, item, run, trial_in_run, key_events):
    """Execute one trial: fixation → prime → pause → target+response → ITI.

    Returns a dict with all the trial-level data.
    """
    item_id = item["item_id"]
    pair_id = item["pair_id"]
    prime_text = item["prime_text"]
    target_text = item["target_text"]
    expected = item["expected_response"]  # 'yes' or 'no'
    critical_region = item.get("critical_region", "")

    # Resolve audio paths
    prime_path = get_audio_path(item_id, pair_id, "prime")
    target_path = get_audio_path(item_id, pair_id, "target")

    if prime_path is None:
        log(f"  WARN: missing prime audio for {item_id} (expected at {PRIME_AUDIO_DIR})")
    if target_path is None:
        log(f"  WARN: missing target audio for {item_id} (expected at {TARGET_AUDIO_DIR})")

    trial_onset_ms = get_time_ms()
    trigger_onset_s = onset_from_trigger_s(trial_onset_ms)

    # --- 1. Fixation ---
    try:
        display_fixation(screen, FIXATION_MS, run=run, trial=trial_in_run,
                         phase="fixation", key_events=key_events)
    except ExperimentAbortRequested:
        raise

    # --- 2. Prime (text + audio synchronized) ---
    prime_start_ms = get_time_ms()
    display_text(screen, prime_text, font_size=TEXT_FONT_SIZE,
                 jp_friendly=False, color=WHITE)
    prime_audio_start, prime_audio_dur = play_audio_blocking(prime_path, PRIME_MAX_MS)
    # Display text for full PRIME_MAX_MS (or audio duration + 200ms, whichever larger, capped)
    if prime_audio_dur:
        prime_display_ms = max(prime_audio_dur + 200, 1500)
        prime_display_ms = min(prime_display_ms, PRIME_MAX_MS)
    else:
        prime_display_ms = PRIME_MAX_MS

    while get_time_ms() - prime_start_ms < prime_display_ms:
        if check_pause():
            pause_dur = handle_pause(screen)
            prime_start_ms += pause_dur
            display_text(screen, prime_text, font_size=TEXT_FONT_SIZE,
                         jp_friendly=False, color=WHITE)
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_during_prime")
            if event.type == KEYDOWN:
                log_key_event(key_events, run, trial_in_run, item_id,
                              "prime", prime_start_ms, event.key)
                if event.key == K_ESCAPE:
                    raise ExperimentAbortRequested("escape_during_prime")
        pygame.time.wait(1)

    # Stop any ongoing prime audio
    pygame.mixer.stop()

    # --- 3. Pause (blank screen between prime and target) ---
    screen.fill(BLACK)
    pygame.display.flip()
    pause_start_ms = get_time_ms()
    while get_time_ms() - pause_start_ms < PAUSE_MS:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_during_pause")
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                raise ExperimentAbortRequested("escape_during_pause")
        pygame.time.wait(1)

    # --- 4. Target (text + audio) + response collection ---
    target_start_ms = get_time_ms()
    display_text(screen, target_text, font_size=TEXT_FONT_SIZE,
                 jp_friendly=False, color=WHITE)
    target_audio_start, target_audio_dur = play_audio_blocking(
        target_path, TARGET_MAX_MS
    )
    # Response window covers from target onset to TARGET_MAX_MS + RESPONSE_WINDOW_MS
    response_deadline_ms = TARGET_MAX_MS + RESPONSE_WINDOW_MS

    response = None
    rt_target_ms = None
    rt_critical_ms = None
    resp_key_name = None
    resp_key_source = None
    while get_time_ms() - target_start_ms < response_deadline_ms:
        if check_pause():
            pause_dur = handle_pause(screen)
            target_start_ms += pause_dur
            display_text(screen, target_text, font_size=TEXT_FONT_SIZE,
                         jp_friendly=False, color=WHITE)
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_during_target")
            if event.type == KEYDOWN:
                event_time_ms, key_name, key_label, key_source = log_key_event(
                    key_events, run, trial_in_run, item_id,
                    "target", target_start_ms, event.key,
                )
                if event.key == K_ESCAPE:
                    raise ExperimentAbortRequested("escape_during_target")
                if normalize_response_key(event.key) == "1" and response is None:
                    response = "1"
                    rt_target_ms = event_time_ms - target_start_ms
                    resp_key_name, resp_key_source = key_name, key_source
                    break  # one response per trial
                elif normalize_response_key(event.key) == "2" and response is None:
                    response = "2"
                    rt_target_ms = event_time_ms - target_start_ms
                    resp_key_name, resp_key_source = key_name, key_source
                    break
        if response is not None:
            # Allow target text to remain visible briefly after response
            # but proceed to next epoch quickly
            break
        pygame.time.wait(1)

    pygame.mixer.stop()

    # --- 5. ITI (jittered blank) ---
    iti_ms = random.randint(ITI_MIN_MS, ITI_MAX_MS)
    screen.fill(BLACK)
    pygame.display.flip()
    iti_start_ms = get_time_ms()
    while get_time_ms() - iti_start_ms < iti_ms:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_during_iti")
            if event.type == KEYDOWN:
                log_key_event(key_events, run, trial_in_run, item_id,
                              "iti", iti_start_ms, event.key)
                if event.key == K_ESCAPE:
                    raise ExperimentAbortRequested("escape_during_iti")
        pygame.time.wait(1)

    # --- 6. Record trial result ---
    response_norm = "yes" if response == "1" else ("no" if response == "2" else None)
    correct = None
    if response_norm is not None and expected is not None:
        correct = 1 if response_norm == expected else 0

    return {
        "run": run,
        "trial": trial_in_run,
        "item_id": item_id,
        "pair_id": pair_id,
        "version": item.get("version", ""),
        "item_type": item.get("item_type", ""),
        "family_id": item.get("family_id", ""),
        "construct": item.get("construct", ""),
        "q_vector": item.get("q_vector", ""),
        "prime_text": prime_text,
        "target_text": target_text,
        "target_lemma": item.get("target_lemma", ""),
        "critical_region": critical_region,
        "expected_response": expected,
        "response": response_norm,
        "response_correct": correct,
        "rt_from_target_onset_ms": rt_target_ms,
        "rt_from_critical_onset_ms": rt_critical_ms,
        "response_key_name": resp_key_name,
        "response_key_source": resp_key_source,
        "prime_audio_onset_ms": (prime_audio_start - first_trigger_time_ms) if prime_audio_start and first_trigger_time_ms else None,
        "prime_audio_duration_ms": prime_audio_dur,
        "target_audio_onset_ms": (target_audio_start - first_trigger_time_ms) if target_audio_start and first_trigger_time_ms else None,
        "target_audio_duration_ms": target_audio_dur,
        "iti_ms": iti_ms,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "onset_from_trigger_s": trigger_onset_s,
    }


# =========================================================
# Saving
# =========================================================

def save_results(results, key_events, exp_info, session_timestamp):
    """Save per-trial results + key events + BIDS-style events.tsv."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    pid = exp_info["Participant"]
    form = exp_info["list_form"]
    prefix = f"sub-{pid}_form-{form}_{session_timestamp}"

    # Results CSV
    results_df = pd.DataFrame(results)
    for col in RESULT_COLUMNS:
        if col not in results_df.columns:
            results_df[col] = None
    results_df["list_form"] = form
    results_df = results_df[RESULT_COLUMNS]
    csv_path = os.path.join(RESULTS_DIR, f"{prefix}_results.csv")
    results_df.to_csv(csv_path, index=False)
    log(f"Results saved: {csv_path}")

    # Key events CSV
    key_events_df = pd.DataFrame(key_events)
    key_events_df["Participant"] = pid
    key_events_df["date"] = exp_info["date"]
    key_events_df["session_timestamp"] = session_timestamp
    for col in KEY_EVENT_COLUMNS:
        if col not in key_events_df.columns:
            key_events_df[col] = None
    key_events_df = key_events_df[KEY_EVENT_COLUMNS]
    ke_path = os.path.join(RESULTS_DIR, f"{prefix}_key_events.csv")
    key_events_df.to_csv(ke_path, index=False)
    log(f"Key events saved: {ke_path}")

    # BIDS-style events.tsv (per run)
    for run in sorted(set(r["run"] for r in results if r["run"])):
        bids_rows = []
        run_trials = [r for r in results if r["run"] == run]
        for r in run_trials:
            if r.get("onset_from_trigger_s") is None:
                continue
            bids_rows.append({
                "onset": r["onset_from_trigger_s"],
                "duration": (FIXATION_MS + PRIME_MAX_MS + PAUSE_MS + TARGET_MAX_MS) / 1000.0,
                "trial_type": r["family_id"],
                "version": r["version"],
                "item_id": r["item_id"],
                "expected": r["expected_response"],
                "response": r["response"],
                "correct": r["response_correct"],
                "rt_target_ms": r["rt_from_target_onset_ms"],
                "target_audio_onset_ms": r["target_audio_onset_ms"],
            })
        if bids_rows:
            bids_path = os.path.join(
                RESULTS_DIR, f"{prefix}_task-grammaticality_run-{int(run):02d}_events.tsv"
            )
            pd.DataFrame(bids_rows).to_csv(bids_path, sep="\t", index=False)
            log(f"BIDS events saved: {bids_path}")

    # Summary stats (accuracy, RT by family)
    summary_rows = []
    if len(results_df) > 0:
        for fam, group in results_df.groupby("family_id"):
            valid = group.dropna(subset=["response_correct"])
            if len(valid):
                acc = valid["response_correct"].mean()
                rt = valid[valid["response_correct"] == 1]["rt_from_target_onset_ms"].mean()
                summary_rows.append({
                    "family_id": fam,
                    "n_trials": len(valid),
                    "accuracy": acc,
                    "mean_rt_correct_ms": rt,
                })
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        s_path = os.path.join(RESULTS_DIR, f"{prefix}_summary.csv")
        summary_df.to_csv(s_path, index=False)
        log(f"Summary saved: {s_path}")


# =========================================================
# Main experiment
# =========================================================

def run_experiment():
    global first_trigger_time_ms

    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(False)

    setup_fonts()
    exp_info = get_participant_info()
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    screen = setup_screen()

    # Load and group items
    try:
        items = load_stimuli(STIMULUS_CSV, exp_info["list_form"])
    except Exception as e:
        screen.fill(BLACK)
        display_text(screen, f"刺激ファイルの読み込みエラー\n\n{e}",
                     font_size=32, color=RED)
        pygame.time.wait(5000)
        pygame.quit()
        return

    runs = split_by_run(items)
    log(f"Trials per run: " + ", ".join(
        [f"R{r}={len(runs[r])}" for r in sorted(runs)]
    ))

    results = []
    key_events = []

    try:
        if not show_instructions(screen):
            pygame.quit()
            return

        # Run 1: wait for trigger; subsequent runs: short rest + trigger
        for run_num in sorted(runs):
            if not wait_for_trigger(screen, key_events, run_label=f"run{run_num}"):
                save_results(results, key_events, exp_info, session_ts)
                pygame.quit()
                return

            # Lead-in rest
            try:
                display_fixation(screen, INITIAL_REST_MS, run=run_num,
                                 trial=0, phase="initial_rest",
                                 key_events=key_events)
            except ExperimentAbortRequested:
                save_results(results, key_events, exp_info, session_ts)
                pygame.quit()
                return

            log(f"Starting run {run_num} ({len(runs[run_num])} trials)")
            for ti, item in enumerate(runs[run_num], start=1):
                try:
                    trial_data = run_trial(screen, item, run_num, ti, key_events)
                    results.append(trial_data)
                except ExperimentAbortRequested as e:
                    log(f"Abort requested: {e}")
                    save_results(results, key_events, exp_info, session_ts)
                    pygame.quit()
                    return

                log(f"  R{run_num} T{ti:02d} {item['item_id']:8s} "
                    f"expected={trial_data['expected_response']:3s} "
                    f"resp={trial_data['response']} "
                    f"rt={trial_data['rt_from_target_onset_ms']}")

            # End-of-run rest
            try:
                display_fixation(screen, FINAL_REST_MS, run=run_num,
                                 trial=len(runs[run_num]) + 1,
                                 phase="end_of_run", key_events=key_events)
            except ExperimentAbortRequested:
                save_results(results, key_events, exp_info, session_ts)
                pygame.quit()
                return

            # Between-run break (skip after last run)
            if run_num < max(runs):
                screen.fill(BLACK)
                display_text(screen,
                             f"Run {run_num} 終了\n\n少し休憩してください。\n\n次のラン開始: トリガー (5) または 5 キー",
                             font_size=INSTRUCTION_FONT_SIZE)
                # Wait either for trigger (handled by next wait_for_trigger)
                # or for fixed rest period if no MR
                pygame.time.wait(2000)  # 2-sec floor before allowing trigger

        # Final exit
        screen.fill(BLACK)
        display_text(screen, "実験終了\n\nお疲れさまでした。", font_size=48)
        pygame.time.wait(3000)
        save_results(results, key_events, exp_info, session_ts)
        pygame.quit()
    except ExperimentAbortRequested as e:
        log(f"Aborted: {e}")
        save_results(results, key_events, exp_info, session_ts)
        pygame.quit()
    except Exception as e:
        log(f"Unexpected error: {e}")
        import traceback
        log(traceback.format_exc())
        save_results(results, key_events, exp_info, session_ts)
        pygame.quit()


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    run_experiment()
