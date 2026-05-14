# Grammaticality Judgment Task (RWL fMRI) — Runner Guide

## Overview

Reading-While-Listening (RWL) grammaticality-judgment task for L1 Japanese
B1-B2 English learners. Implements the v3 CDM/CAT stimulus bank
(216 items: 168 critical + 48 fillers) across 4 fMRI runs.

## File Structure

```
Experiment/fMRI/
├── Grammaticality_RWL_fMRI.py        # Main experiment script
├── README_Grammaticality.md          # This file
├── tts_generate_audio.py             # TTS audio generation helper
├── audio_grammaticality/
│   ├── prime/                        # Prime audio files (132 .wav)
│   │   ├── P001.wav                  # Critical: per pair_id
│   │   ├── P002.wav
│   │   ├── ...
│   │   ├── GF01.wav                  # Filler: per item_id
│   │   └── ...
│   └── target/                       # Target audio files (216 .wav)
│       ├── P001G.wav                 # Critical: per item_id (G/U distinct)
│       ├── P001U.wav
│       ├── ...
│       ├── GF01.wav
│       └── ...
└── results_grammaticality/           # Output directory (auto-created)
    ├── sub-001_form-A_YYYYMMDD_HHMMSS_results.csv
    ├── sub-001_form-A_YYYYMMDD_HHMMSS_key_events.csv
    ├── sub-001_form-A_YYYYMMDD_HHMMSS_summary.csv
    └── sub-001_form-A_YYYYMMDD_HHMMSS_task-grammaticality_run-01_events.tsv  # BIDS
```

## Prerequisites

```bash
pip install pygame pandas numpy scipy
```

For audio generation (one-time):
```bash
pip install boto3        # Amazon Polly
# or use OpenAI TTS:
pip install openai
```

## Running the Experiment

### Option 1: Pygame (fMRI scanner)

```bash
cd /Users/ryuya/Library/CloudStorage/Dropbox/fMRI_Grammaticality/Experiment/fMRI
python3 Grammaticality_RWL_fMRI.py
```

Prompts:
- Participant ID (e.g., "001")
- Latin-square Form: A or B (auto-assigned by parity if blank)

### Option 2: Streamlit Web (behavioral pilot)

```bash
cd /Users/ryuya/Library/CloudStorage/Dropbox/fMRI_Grammaticality/Experiment/fMRI
./launch_web.sh
# OR: streamlit run Grammaticality_RWL_Web.py
```

Then open `http://localhost:8501` in a browser.

**Web-specific features**:
- Auto-trigger every N seconds (default 2s) at each run-start checkpoint
- Optional continuous TR-simulation mode (fires trigger every N seconds throughout)
- Responses via on-screen buttons or keyboard
- Results downloadable as CSV from browser

Configure via the sidebar before pressing "Start Experiment".

## Trial Structure

| Stage | Duration | Display | Audio |
|---|---|---|---|
| Fixation | 500 ms | `+` | — |
| **Prime** | ~3500 ms | full prime sentence | prime.wav |
| Blank | 500 ms | (blank) | — |
| **Target + response** | ~4500 ms | full target sentence | target.wav |
| ITI | 500-2500 ms (jittered) | (blank) | — |
| **Total** | **~8-10 sec** | | |

Critical region time-locking is computed downstream from forced-alignment data.

## Keys

| Key | Function |
|---|---|
| `1` | "Grammatical in this context" (yes response) |
| `2` | "Not grammatical in this context" (no response) |
| `5` | fMRI trigger / continue to next run |
| `Esc` | Abort experiment (saves data) |
| `Cmd+Shift+Esc` | Pause / resume |

## Run Structure

4 runs per participant, ~33 trials each, ~5 min per run:
- Each run starts with trigger wait
- 10-sec lead-in fixation
- 32-34 trials (32-34 × ~8-10 sec ≈ 4.5 min)
- 10-sec end-of-run rest
- Inter-run break (self-paced, trigger to continue)

Total task time: ~22-25 min + scanner overhead.

## Latin-Square Assignment

| Participant ID | Form |
|---|---|
| Odd (001, 003, 005...) | A |
| Even (002, 004, 006...) | B |

Form A: G of P001-P042 + U of P043-P084 + all 48 fillers (132 items)
Form B: U of P001-P042 + G of P043-P084 + all 48 fillers (132 items)

## Output Files

### `*_results.csv` (per-trial)
Columns: run, trial, item_id, pair_id, version, item_type, family_id,
construct, q_vector, prime_text, target_text, target_lemma, critical_region,
expected_response, response, response_correct, rt_from_target_onset_ms,
prime_audio_onset_ms, target_audio_onset_ms, iti_ms, time,
onset_from_trigger_s, list_form.

### `*_key_events.csv` (every keypress)
Columns: Participant, date, session_timestamp, run, trial, item_id, phase,
key_code, key_name, key_label, key_source, normalized_response,
phase_time_ms, time, onset_from_trigger_s.

### `*_summary.csv` (per-WF accuracy + RT)
Columns: family_id, n_trials, accuracy, mean_rt_correct_ms.

### `*_task-grammaticality_run-NN_events.tsv` (BIDS format, one per run)
Standard BIDS event file for fMRI analysis pipelines.

## Audio File Generation

Run `tts_generate_audio.py` once to generate all 348 audio files (132 primes + 216 targets):

```bash
python3 tts_generate_audio.py --service polly --voice Joanna
# or
python3 tts_generate_audio.py --service openai --voice nova
```

**F02 SSML override**: the script automatically applies the phoneme override
for the 6 F02 U items (P007U-P012U) when using Polly Neural.

**F01 U padding**: post-generation, the script pads the 6 F01 U targets
with 370 ms trailing silence.

**Forced alignment** (after generation):
```bash
# Optional: use Gentle / Montreal Forced Aligner / whisperX
# to compute critical_word_onset_ms_aligned column.
```

## Dry-Run Testing (without audio)

Set `DRY_RUN = True` near the top of `Grammaticality_RWL_fMRI.py` to:
- Skip audio loading
- Use fixed mock durations
- Allow keyboard-driven debugging in windowed (non-fullscreen) mode

(Implementation: set `--dry-run` flag once added; otherwise inspect `play_audio_blocking()`.)

## Troubleshooting

| Symptom | Fix |
|---|---|
| "音声ファイルが見つかりません" | Verify `audio_grammaticality/prime/` and `target/` contain the expected `.wav` files |
| "Stimulus CSV not found" | Verify path to `stimulus_master_cdm_cat_v3.csv` |
| Pygame fullscreen issues | Try `pygame.RESIZABLE` flag instead, or check display config |
| Trigger not detected | Verify scanner-keyboard mapping for `5` |
| F02 audio sounds wrong (auto-corrected "a" → "an") | Use SSML phoneme override (see tts_generate_audio.py) |
| Long primes (>8 words) overrun PRIME_MAX_MS | Increase PRIME_MAX_MS in script or shorten prime text |

## Validation Before Scanning

1. Run with dummy participant ID outside scanner
2. Verify all 132 items load
3. Check audio timing (prime ≤3.3 sec, target ≤2.4 sec)
4. Verify response logging (use a few practice responses)
5. Check trigger detection
6. Verify BIDS event file output

## Pilot Phase Checklist

- [ ] All 348 audio files generated and verified
- [ ] F02 SSML override applied (6 items audio QA'd)
- [ ] F01 U trailing silence padded (6 items)
- [ ] Run pre-scan dry-run with 1 participant
- [ ] Run full pilot on 12-15 B1-B2 JP learners
- [ ] Analyze per-WF accuracy and RT
- [ ] Exclude items at floor (<20%) or ceiling (>95%)
- [ ] Decide go/no-go for fMRI

## References

- Stimulus bank: `../../Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/stimulus_master_cdm_cat_v3.csv`
- Methods: `../../Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/methods.md`
- Pilot protocol: `../../Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/pilot_protocol.md`
- Pre-registration: `../../Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/preregistration_template.md`
