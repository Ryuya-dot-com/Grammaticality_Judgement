# Grammaticality Judgement (RWL fMRI)

A Reading-While-Listening grammaticality-judgment task for L1 Japanese B1–B2
English learners. Designed as a 2×2 (concreteness × count/mass) fMRI study
with a fully balanced 14-word-family stimulus bank.

> 🌐 **Live demo (browser pilot)**: https://ryuya-dot-com.github.io/Grammaticality_Judgement/

## Quick Start

### Try the browser version

Open the deployed URL above, or run locally:
```bash
cd Experiment/web_static
python3 -m http.server 8000
# Browse to http://localhost:8000
```

### Run the fMRI Pygame version

```bash
cd Experiment/fMRI
pip install pygame pandas numpy scipy
python3 Grammaticality_RWL_fMRI.py
```

## Repository Structure

```
.
├── Grammaticality_Judgement_CAT/
│   └── stimuli/refined_cdm_cat/
│       ├── stimulus_master_cdm_cat_v3.csv       # 216-item master (final)
│       ├── methods.md                           # Design rationale
│       ├── pilot_protocol.md                    # Behavioral pilot procedure
│       └── preregistration_template.md          # OSF pre-reg template
│
├── Experiment/
│   ├── fMRI/                                    # Pygame for fMRI scanning
│   │   ├── Grammaticality_RWL_fMRI.py
│   │   ├── Grammaticality_RWL_Web.py            # Streamlit alternative
│   │   ├── tts_generate_audio.py                # Polly/OpenAI TTS
│   │   ├── forced_align_audio.py                # Word-onset extraction
│   │   └── README_Grammaticality.md
│   │
│   └── web_static/                              # GitHub Pages-deployable
│       ├── index.html / style.css / experiment.js
│       ├── stimuli.json                         # 216 items
│       ├── audio/{prime,target}/                # TTS .wav files
│       ├── tts_macos_say.py                     # macOS `say` based TTS
│       └── convert_csv_to_json.py
│
└── .github/workflows/
    └── deploy-pages.yml                         # Auto-deploy to GitHub Pages
```

## Stimulus Bank Overview

- **216 items** = 168 critical (84 G/U pairs × 2) + 48 fillers
- **14 word families** (F01–F14) × 6 pairs each
- Each pair tests one grammatical construct (article omission, plural marking,
  mass/count quantifier, etc.) on minimally different sentence pairs
- **2×2 dissociation** of concreteness × grammar built into F03/F04/F13/F14
- **Latin-square A/B forms** for within-subject counterbalancing

| Word Family | Construct (G vs U) | Example |
|---|---|---|
| F01 | sg count + article omission | `Maya bought a lamp yesterday.` vs `Maya bought lamp yesterday.` |
| F02 | a/an allomorph | `Sara ate an orange.` vs `Sara ate a orange.` |
| F03 | count + numeral + plural | `Maya picked five apples.` vs `Maya picked five apple.` |
| F04 | abstract mass + many/much | `Maya gained much knowledge.` vs `many knowledge` |
| F05 | count + many/much | `Maya borrowed many books.` vs `much books` |
| F06 | abstract mass + a/some | `some helpful advice` vs `a helpful advice` |
| F07 | mass + plural -s | `wonderful music` vs `wonderful musics` |
| F08 | count→mass food coercion | `too much carrot` (after grating) vs `too many carrot` |
| F09 | mass→serving count | `three coffees` (at cafe) vs `three coffee` |
| F10 | mass→kind count | `These wines taste mild.` vs `These wine taste mild.` |
| F11 | fixed noncount + plural | `beautiful furniture` vs `beautiful furnitures` |
| F12 | plurale tantum + agreement | `These jeans look comfortable.` vs `This jeans looks comfortable.` |
| F13 | **concrete mass + many/much (new)** | `much plastic` vs `many plastic` |
| F14 | **abstract count + plural after numeral (new)** | `three topics` vs `three topic` |

## Web Experiment Features

- Pure HTML/JS, no server backend
- 4 runs × ~33 trials per session (~22 min)
- Manual run start; trials auto-progress
- Three presentation modes: RWL / text-only / audio-only
- Detailed timing controls in setup form
- CSV download of results + key events
- Per-WF accuracy + RT summary at completion

## Citation

If you use this stimulus bank or task in your research, please cite:
```
TBD: Komuro, R. (2026). Grammaticality Judgement RWL fMRI bank v3.
https://github.com/Ryuya-dot-com/Grammaticality_Judgement
```

## License

Research-use only. Contact the author for collaboration or licensing inquiries.

## Background

Designed and validated through:
- Multi-round agent-assisted audits (lexical frequency, AoA, concreteness,
  prime quality, Q-matrix psychometrics, fMRI feasibility)
- 84 critical pairs covering 14 syntactic constructs
- 50/50 gender-balanced names (16 names × ~5 uses each)
- All target lemmas Zipf ≥ 3.5, CEFR-J ≤ B2 (Japanese B1-B2 learner accessible)

See [methods.md](Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/methods.md)
for full design rationale.
