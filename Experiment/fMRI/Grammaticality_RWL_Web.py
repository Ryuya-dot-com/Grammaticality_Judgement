#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grammaticality Judgment Task — Streamlit Web Version

Reading-While-Listening (RWL) grammaticality-judgment task for behavioral pilot
on the web. Same stimulus bank as the Pygame fMRI version
(stimulus_master_cdm_cat_v3.csv), but adapted for browser-based execution.

Key differences from the fMRI version:
- Trigger '5' is fired AUTOMATICALLY every N seconds (default 2s) at each
  trigger checkpoint, instead of waiting for manual key press.
- Optional continuous TR-simulation mode (fires '5' every N seconds throughout).
- Responses collected via keyboard ('1' / '2') or buttons (Yes / No).
- Results downloadable as CSV from the browser.

Usage:
    cd /Users/ryuya/Library/CloudStorage/Dropbox/fMRI_Grammaticality/Experiment/fMRI
    streamlit run Grammaticality_RWL_Web.py

Then open the URL shown in terminal (usually http://localhost:8501).
"""

import base64
import io
import os
import random
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# =========================================================
# Constants
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
STIMULUS_CSV = (
    SCRIPT_DIR / ".." / ".." /
    "Grammaticality_Judgement_CAT" / "stimuli" / "refined_cdm_cat" /
    "stimulus_master_cdm_cat_v3.csv"
).resolve()
PRIME_AUDIO_DIR = (SCRIPT_DIR / "audio_grammaticality" / "prime").resolve()
TARGET_AUDIO_DIR = (SCRIPT_DIR / "audio_grammaticality" / "target").resolve()

# Trial timing (ms)
FIXATION_MS = 500
PRIME_MAX_MS = 3500
PAUSE_MS = 500
TARGET_MAX_MS = 2500
RESPONSE_WINDOW_MS = 2500
ITI_MIN_MS = 500
ITI_MAX_MS = 2500

# Run rest periods
INITIAL_REST_MS = 4000
END_OF_RUN_REST_MS = 4000

# Auto-refresh interval for state-machine progression (ms)
REFRESH_INTERVAL_MS = 100

# Audio playback: convert to data URL for autoplay
AUDIO_AUTOPLAY_HTML = """
<audio id="trial_audio" autoplay>
    <source src="data:audio/{mime};base64,{b64}" type="audio/{mime}">
</audio>
"""

# =========================================================
# Page setup
# =========================================================

st.set_page_config(
    page_title="Grammaticality Judgment (RWL)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Session state init
# =========================================================

def init_state():
    defaults = {
        "phase": "intro",                # state machine phase
        "participant_id": "",
        "list_form": "A",
        "stimuli": None,                  # list of all items for current form
        "runs": None,                     # dict: run_num → list of items
        "current_run": 1,
        "trial_in_run": 0,                # 1-indexed
        "trial_phase": "fixation",        # phase within trial
        "trial_phase_start_time": None,   # time.time() at phase start
        "trial_start_time": None,
        "session_start_time": None,
        "results": [],
        "key_events": [],
        "session_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "current_response": None,
        "current_response_time": None,
        "current_iti_ms": 1500,
        "audio_played": False,
        "audio_b64_cache": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# =========================================================
# Helpers
# =========================================================

def now_ms():
    return time.perf_counter() * 1000


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def session_onset_s(t=None):
    """Seconds since session start."""
    if st.session_state.session_start_time is None:
        return None
    if t is None:
        t = time.time()
    return t - st.session_state.session_start_time


def load_stimuli(form):
    """Load CSV and filter for form."""
    if not STIMULUS_CSV.exists():
        return None
    df = pd.read_csv(STIMULUS_CSV, dtype={"q_vector": str})
    sub = df[df["list_form"].isin([form, "AB"])].copy()
    run_col = f"run_assignment_{form}"
    trial_col = f"trial_index_{form}"
    sub = sub.dropna(subset=[run_col, trial_col]).copy()
    sub["run_int"] = sub[run_col].astype(int)
    sub["trial_int"] = sub[trial_col].astype(int)
    sub = sub.sort_values(["run_int", "trial_int"]).reset_index(drop=True)
    return sub.to_dict(orient="records")


def split_by_run(items):
    runs = {1: [], 2: [], 3: [], 4: []}
    for it in items:
        runs[it["run_int"]].append(it)
    return runs


def get_audio_b64(item_id, pair_id, kind):
    """Read audio file and return base64-encoded data URL string + mime."""
    cache_key = f"{kind}_{pair_id if kind == 'prime' else item_id}"
    if cache_key in st.session_state.audio_b64_cache:
        return st.session_state.audio_b64_cache[cache_key]

    if kind == "prime":
        stem = pair_id
        base = PRIME_AUDIO_DIR
    else:
        stem = item_id
        base = TARGET_AUDIO_DIR

    for ext, mime in [(".wav", "wav"), (".mp3", "mpeg")]:
        path = base / f"{stem}{ext}"
        if path.exists():
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            st.session_state.audio_b64_cache[cache_key] = (b64, mime)
            return (b64, mime)
    return (None, None)


def render_audio_autoplay(b64, mime, key="audio"):
    """Embed HTML5 audio with autoplay."""
    if b64 is None:
        return
    html = AUDIO_AUTOPLAY_HTML.format(b64=b64, mime=mime)
    st.components.v1.html(html, height=0)


def render_trial_text(text, font_size=48, color="#FFFFFF"):
    """Render trial text centered in main area."""
    st.markdown(
        f"""
        <div style="
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: {font_size}px;
            color: {color};
            text-align: center;
            font-family: 'Helvetica', sans-serif;
            white-space: nowrap;
            ">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_fixation(font_size=72):
    render_trial_text("+", font_size=font_size, color="#FFFFFF")


def black_screen():
    st.markdown(
        """
        <style>
        .stApp {background-color: #000000;}
        section[data-testid="stSidebar"] {background-color: #1a1a1a;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def log_run_start():
    """Record the start of a run."""
    if st.session_state.session_start_time is None:
        st.session_state.session_start_time = time.time()
    st.session_state.key_events.append({
        "run": st.session_state.current_run,
        "trial": 0,
        "item_id": "RUN_START",
        "phase": "run_start",
        "key_code": None,
        "key_name": None,
        "key_label": None,
        "key_source": "auto",
        "normalized_response": None,
        "phase_time_ms": 0,
        "time": now_iso(),
        "onset_from_trigger_s": session_onset_s(),
    })


def record_response(key_label):
    """Record participant response."""
    if st.session_state.current_response is not None:
        return
    if key_label not in ("1", "2"):
        return
    st.session_state.current_response = key_label
    elapsed_ms = (time.time() - st.session_state.trial_phase_start_time) * 1000
    st.session_state.current_response_time = elapsed_ms
    st.session_state.key_events.append({
        "run": st.session_state.current_run,
        "trial": st.session_state.trial_in_run,
        "item_id": (
            st.session_state.runs[st.session_state.current_run]
            [st.session_state.trial_in_run - 1]["item_id"]
            if st.session_state.trial_in_run > 0 else ""
        ),
        "phase": st.session_state.trial_phase,
        "key_code": 49 if key_label == "1" else 50,
        "key_name": key_label,
        "key_label": key_label,
        "key_source": "button",
        "normalized_response": key_label,
        "phase_time_ms": elapsed_ms,
        "time": now_iso(),
        "onset_from_trigger_s": session_onset_s(),
    })


def finalize_trial(item):
    """Save trial results and advance state."""
    response_norm = (
        "yes" if st.session_state.current_response == "1"
        else "no" if st.session_state.current_response == "2"
        else None
    )
    correct = None
    if response_norm and item.get("expected_response"):
        correct = 1 if response_norm == item["expected_response"] else 0

    st.session_state.results.append({
        "run": st.session_state.current_run,
        "trial": st.session_state.trial_in_run,
        "item_id": item["item_id"],
        "pair_id": item["pair_id"],
        "version": item.get("version", ""),
        "item_type": item.get("item_type", ""),
        "family_id": item.get("family_id", ""),
        "construct": item.get("construct", ""),
        "q_vector": item.get("q_vector", ""),
        "prime_text": item["prime_text"],
        "target_text": item["target_text"],
        "target_lemma": item.get("target_lemma", ""),
        "critical_region": item.get("critical_region", ""),
        "expected_response": item.get("expected_response"),
        "response": response_norm,
        "response_correct": correct,
        "rt_from_target_onset_ms": st.session_state.current_response_time,
        "iti_ms": st.session_state.current_iti_ms,
        "time": now_iso(),
        "onset_from_trigger_s": session_onset_s(),
        "list_form": st.session_state.list_form,
    })

    # Reset trial-specific state
    st.session_state.current_response = None
    st.session_state.current_response_time = None
    st.session_state.audio_played = False


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:
    st.title("🧠 Grammaticality RWL")
    st.caption("Streamlit Web Pilot")

    if st.session_state.phase == "intro":
        st.subheader("Session Setup")
        pid = st.text_input(
            "Participant ID",
            value=st.session_state.participant_id or "",
            placeholder="e.g., 001",
        )
        form = st.selectbox(
            "Latin-square Form",
            options=["A", "B"],
            index=0 if st.session_state.list_form == "A" else 1,
        )

        st.divider()
        if st.button("▶️ Start Experiment", type="primary", use_container_width=True):
            if not pid:
                pid = datetime.now().strftime("%Y%m%d%H%M%S")
            st.session_state.participant_id = pid
            st.session_state.list_form = form
            stimuli = load_stimuli(form)
            if stimuli is None:
                st.error(f"Stimulus CSV not found at {STIMULUS_CSV}")
            else:
                st.session_state.stimuli = stimuli
                st.session_state.runs = split_by_run(stimuli)
                st.session_state.phase = "instructions"
                st.session_state.current_run = 1
                st.session_state.trial_in_run = 0
                st.rerun()
    else:
        st.write(f"**Participant**: {st.session_state.participant_id}")
        st.write(f"**Form**: {st.session_state.list_form}")
        st.write(f"**Run**: {st.session_state.current_run} / 4")
        st.write(f"**Trial**: {st.session_state.trial_in_run} / "
                 f"{len(st.session_state.runs[st.session_state.current_run]) if st.session_state.runs else 0}")
        st.write(f"**Phase**: `{st.session_state.trial_phase}`")
        st.divider()

        if st.button("⏸ Pause", use_container_width=True):
            st.session_state.phase = "paused"
            st.rerun()
        if st.button("⏹ Abort + Save", use_container_width=True):
            st.session_state.phase = "complete"
            st.rerun()

    # Response buttons (always visible during trial)
    if st.session_state.phase == "running":
        st.divider()
        st.subheader("Response")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Grammatical (1)", use_container_width=True):
                record_response("1")
        with col2:
            if st.button("❌ Not Grammatical (2)", use_container_width=True):
                record_response("2")
        st.caption("Or use keys: 1 / 2 (focus must be on page)")


# =========================================================
# Main area: phase-driven content
# =========================================================

# Apply black background
black_screen()

# Auto-refresh for state machine progression
if st.session_state.phase in ("running", "paused"):
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key=f"refresh_{st.session_state.phase}")


# Keyboard capture via JavaScript (best-effort; Streamlit limitation)
if st.session_state.phase == "running":
    st.components.v1.html(
        """
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === '1' || e.key === '2') {
                // Use Streamlit's key event passing (limited)
                // For now, instruct user to use buttons
                console.log('Key pressed:', e.key);
            }
        }, {once: false});
        </script>
        """,
        height=0,
    )


# ---- INTRO ----
if st.session_state.phase == "intro":
    st.markdown(
        """
        <div style="color: #FFFFFF; padding: 2rem;">
        <h1>Grammaticality Judgment Task</h1>
        <h3>Reading-While-Listening (Web Pilot)</h3>
        <p>サイドバーで参加者IDとフォームを選び、開始ボタンを押してください。</p>
        <hr/>
        <p><strong>このページの設計</strong>:</p>
        <ul>
            <li>各試行で、画面に文 (prime) が表示され、同時に音声が流れます。</li>
            <li>短い間の後、判断対象の文 (target) が表示されます。</li>
            <li><b>文法的に正しい</b> 場合は サイドバーの「Grammatical (1)」</li>
            <li><b>正しくない</b> 場合は「Not Grammatical (2)」を押してください。</li>
            <li>または、キーボードの <kbd>1</kbd> / <kbd>2</kbd> を使用できます。</li>
        </ul>
        <p><em>進行</em>: 各ランはボタンで手動開始し、その後の試行は自動進行します。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---- INSTRUCTIONS ----
elif st.session_state.phase == "instructions":
    st.markdown(
        """
        <div style="color: #FFFFFF; padding: 2rem; max-width: 800px; margin: auto;">
        <h2>これから実験を開始します</h2>
        <p>各試行は次のように進みます:</p>
        <ol>
            <li>場面を説明する文（プライム）</li>
            <li>短い間</li>
            <li>判断対象の文（ターゲット）</li>
        </ol>
        <p>判断対象の文がその場面で<strong>文法的に正しい</strong>場合は<br/>
            <kbd>1</kbd> または「Grammatical」ボタン</p>
        <p><strong>正しくない</strong>場合は<br/>
            <kbd>2</kbd> または「Not Grammatical」ボタン</p>
        <hr/>
        <p>4ランの実験です。各ランの開始ボタンを押すと自動で進行します。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("▶️ Begin Run 1", type="primary"):
        st.session_state.phase = "running"
        st.session_state.trial_phase = "initial_rest"
        st.session_state.trial_phase_start_time = time.time()
        log_run_start()
        st.rerun()

# ---- PAUSED ----
elif st.session_state.phase == "paused":
    st.markdown(
        """
        <div style="color: #FFFFFF; padding: 2rem; text-align: center;">
        <h2>⏸ Paused</h2>
        <p>サイドバーから再開してください。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("▶️ Resume", type="primary"):
        st.session_state.phase = "running"
        st.session_state.trial_phase_start_time = time.time()
        st.rerun()

# ---- RUNNING (state machine) ----
elif st.session_state.phase == "running":
    # Current trial item
    if st.session_state.trial_in_run == 0:
        current_item = None
    else:
        run_items = st.session_state.runs[st.session_state.current_run]
        idx = st.session_state.trial_in_run - 1
        current_item = run_items[idx] if idx < len(run_items) else None

    phase = st.session_state.trial_phase
    phase_start = st.session_state.trial_phase_start_time
    elapsed_s = time.time() - phase_start
    elapsed_ms = elapsed_s * 1000

    # ===== State transitions =====

    if phase == "initial_rest":
        render_fixation()
        if elapsed_ms >= INITIAL_REST_MS:
            st.session_state.trial_in_run = 1
            st.session_state.trial_phase = "fixation"
            st.session_state.trial_phase_start_time = time.time()
            st.session_state.trial_start_time = time.time()
            st.rerun()

    elif phase == "fixation":
        render_fixation()
        if elapsed_ms >= FIXATION_MS:
            st.session_state.trial_phase = "prime"
            st.session_state.trial_phase_start_time = time.time()
            st.session_state.audio_played = False
            st.rerun()

    elif phase == "prime":
        if current_item:
            # Play audio once at phase entry
            if not st.session_state.audio_played:
                b64, mime = get_audio_b64(current_item["item_id"], current_item["pair_id"], "prime")
                if b64:
                    render_audio_autoplay(b64, mime, key=f"prime_{current_item['item_id']}")
                st.session_state.audio_played = True
            render_trial_text(current_item["prime_text"], font_size=48)
        if elapsed_ms >= PRIME_MAX_MS:
            st.session_state.trial_phase = "pause"
            st.session_state.trial_phase_start_time = time.time()
            st.rerun()

    elif phase == "pause":
        # blank screen
        if elapsed_ms >= PAUSE_MS:
            st.session_state.trial_phase = "target"
            st.session_state.trial_phase_start_time = time.time()
            st.session_state.audio_played = False
            st.rerun()

    elif phase == "target":
        if current_item:
            if not st.session_state.audio_played:
                b64, mime = get_audio_b64(current_item["item_id"], current_item["pair_id"], "target")
                if b64:
                    render_audio_autoplay(b64, mime, key=f"target_{current_item['item_id']}")
                st.session_state.audio_played = True
            render_trial_text(current_item["target_text"], font_size=48, color="#FFD700")
        # Allow early response transition
        if st.session_state.current_response is not None or elapsed_ms >= (TARGET_MAX_MS + RESPONSE_WINDOW_MS):
            st.session_state.trial_phase = "iti"
            st.session_state.trial_phase_start_time = time.time()
            st.session_state.current_iti_ms = random.randint(ITI_MIN_MS, ITI_MAX_MS)
            st.rerun()

    elif phase == "iti":
        # blank
        if elapsed_ms >= st.session_state.current_iti_ms:
            # Finalize current trial
            if current_item:
                finalize_trial(current_item)
            # Advance to next trial or end of run
            run_items = st.session_state.runs[st.session_state.current_run]
            if st.session_state.trial_in_run >= len(run_items):
                st.session_state.trial_phase = "end_of_run"
                st.session_state.trial_phase_start_time = time.time()
            else:
                st.session_state.trial_in_run += 1
                st.session_state.trial_phase = "fixation"
                st.session_state.trial_phase_start_time = time.time()
            st.rerun()

    elif phase == "end_of_run":
        render_fixation()
        if elapsed_ms >= END_OF_RUN_REST_MS:
            if st.session_state.current_run >= 4:
                st.session_state.phase = "complete"
                st.rerun()
            else:
                st.session_state.trial_phase = "inter_run_rest"
                st.session_state.trial_phase_start_time = time.time()
                st.rerun()

    elif phase == "inter_run_rest":
        st.markdown(
            f"""
            <div style="color: #FFFFFF; text-align: center; padding-top: 25vh;">
                <h2>Run {st.session_state.current_run} 終了</h2>
                <p>少し休憩してください。</p>
                <p>準備ができたら下のボタンで次のランを開始してください。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"▶️ Begin Run {st.session_state.current_run + 1}", type="primary"):
            st.session_state.current_run += 1
            st.session_state.trial_in_run = 0
            st.session_state.trial_phase = "initial_rest"
            st.session_state.trial_phase_start_time = time.time()
            log_run_start()
            st.rerun()

# ---- COMPLETE ----
elif st.session_state.phase == "complete":
    st.markdown(
        """
        <div style="color: #FFFFFF; padding: 2rem; max-width: 800px; margin: auto;">
        <h1>🎉 実験終了</h1>
        <p>お疲れさまでした。結果をダウンロードしてください。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.results:
        results_df = pd.DataFrame(st.session_state.results)
        st.subheader("Trial Results")
        st.dataframe(results_df, use_container_width=True, height=400)

        # Summary
        if "family_id" in results_df.columns:
            summary = (results_df
                       .dropna(subset=["response_correct"])
                       .groupby("family_id")
                       .agg(n_trials=("response_correct", "count"),
                            accuracy=("response_correct", "mean"),
                            mean_rt_ms=("rt_from_target_onset_ms", "mean")))
            st.subheader("Per-WF Summary")
            st.dataframe(summary, use_container_width=True)

        # Downloads
        csv_buf = io.StringIO()
        results_df.to_csv(csv_buf, index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv_buf.getvalue(),
            file_name=(
                f"sub-{st.session_state.participant_id}_form-{st.session_state.list_form}_"
                f"{st.session_state.session_timestamp}_results.csv"
            ),
            mime="text/csv",
        )

        # Key events
        if st.session_state.key_events:
            kev_df = pd.DataFrame(st.session_state.key_events)
            kev_buf = io.StringIO()
            kev_df.to_csv(kev_buf, index=False)
            st.download_button(
                label="📥 Download Key Events CSV",
                data=kev_buf.getvalue(),
                file_name=(
                    f"sub-{st.session_state.participant_id}_form-{st.session_state.list_form}_"
                    f"{st.session_state.session_timestamp}_key_events.csv"
                ),
                mime="text/csv",
            )

    if st.button("🔄 Start New Session"):
        # Reset all state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
