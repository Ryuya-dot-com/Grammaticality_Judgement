# Grammaticality Judgment Task — Static Web Version

A pure HTML/CSS/JavaScript implementation of the Reading-While-Listening (RWL)
grammaticality-judgment task. Runs entirely in the browser, no server required,
deployable to GitHub Pages or any static host.

## File Structure

```
web_static/
├── index.html                # Main page
├── style.css                 # Styles
├── experiment.js             # Trial loop + state machine + CSV download
├── stimuli.json              # 216 items (generated from CSV)
├── convert_csv_to_json.py    # Regenerate stimuli.json from master CSV
├── audio/
│   ├── prime/                # Prime audio files (.wav)
│   │   ├── P001.wav          # critical: pair_id
│   │   ├── ...
│   │   └── GF01.wav          # filler: item_id
│   └── target/               # Target audio files (.wav)
│       ├── P001G.wav         # critical: item_id (G/U distinct)
│       ├── ...
│       └── UF24.wav
└── README.md                 # This file
```

## Quick Start (Local Testing)

```bash
cd Experiment/web_static
python3 -m http.server 8000
```

Open `http://localhost:8000` in a browser.

Or any other static server:
```bash
npx serve .
# or
php -S localhost:8000
```

## Features

- **No server required** — pure static HTML/JS, runs entirely client-side
- **GitHub Pages compatible** — drop into `docs/` or `gh-pages` branch
- **Responsive flow**: Setup → Instructions → 4 runs × ~33 trials → Complete
- **Manual run start**: each run begins when user clicks "Begin Run N"
  (no auto-trigger; suitable for self-paced behavioral pilot)
- **RWL synchronized**: text + audio start simultaneously per trial
- **Configurable timings**: detailed settings in the setup form
- **Three presentation modes**: RWL / text-only / audio-only
- **CSV downloads**: results + key events
- **Keyboard shortcuts**: `1` / `2` for response, `Esc` to abort
- **Pause/Resume**: any time during the experiment
- **Live summary**: per-WF accuracy and RT shown after completion

## Regenerating stimuli.json

If the master CSV changes:
```bash
python3 convert_csv_to_json.py
```

This rebuilds `stimuli.json` from
`../../Grammaticality_Judgement_CAT/stimuli/refined_cdm_cat/stimulus_master_cdm_cat_v3.csv`.

## Audio Files

Audio files are NOT included in this directory by default (they're generated
via TTS). To populate:

1. Generate audio via Polly/OpenAI:
   ```bash
   cd ../fMRI
   python3 tts_generate_audio.py --service polly --voice Joanna
   ```
2. Copy generated `.wav` files from `Experiment/fMRI/audio_grammaticality/`
   to `Experiment/web_static/audio/`:
   ```bash
   cp -r ../fMRI/audio_grammaticality/prime/* audio/prime/
   cp -r ../fMRI/audio_grammaticality/target/* audio/target/
   ```

Audio formats: `.wav` preferred (MP3 also supported by browsers).

## GitHub Pages Deployment

### Option 1: `docs/` folder in main repo (recommended for monorepo)

```bash
# At the repo root:
mkdir -p docs
cp -r Experiment/web_static/* docs/
git add docs/
git commit -m "Add web-static grammaticality task"
git push origin main
```

Then in GitHub:
1. Go to **Settings → Pages**
2. Under **Source**, select `Deploy from a branch`
3. Branch: `main`, folder: `/docs`
4. Save → wait ~1 min → access at `https://<username>.github.io/<repo>/`

### Option 2: Dedicated `gh-pages` branch

```bash
# Create orphan branch with only web_static contents
git checkout --orphan gh-pages
git rm -rf .
cp -r Experiment/web_static/* .
git add .
git commit -m "Initial gh-pages deployment"
git push origin gh-pages
```

Then in GitHub Settings → Pages → Source: `gh-pages` branch, `/` (root).

### Option 3: Separate dedicated repo

Create a new public repo `grammaticality-rwl-web`, copy `web_static/*` files,
push to `main`, and enable Pages on `main` branch root.

### URL structure on GitHub Pages

```
https://<user>.github.io/<repo>/                  # → index.html
https://<user>.github.io/<repo>/stimuli.json      # → stimulus list
https://<user>.github.io/<repo>/audio/prime/P001.wav
https://<user>.github.io/<repo>/audio/target/P001G.wav
```

### File size considerations

- `stimuli.json`: ~100 KB
- Each audio file: ~30-100 KB (~2 sec at 44.1kHz mono)
- Total audio (348 files): ~20-30 MB
- GitHub repo limit: 1 GB recommended (5 GB hard limit)
- **For larger audio**: use GitHub LFS or external CDN (e.g., R2, Cloudflare Pages)

## Browser Compatibility

| Browser | Status |
|---|---|
| Chrome / Edge (Chromium) | ✅ Full support |
| Firefox | ✅ Full support |
| Safari | ⚠️ Audio autoplay may require user gesture |
| Mobile Safari (iOS) | ⚠️ Same autoplay caveat |

**Autoplay note**: Modern browsers block audio autoplay until user has
interacted with the page. The "Begin Run 1" button click satisfies this
requirement, so subsequent audio playback works automatically.

## Timing Precision

- JavaScript timer precision: ~5-15 ms (limited by browser event loop)
- Audio onset latency: ~30-100 ms (depends on browser/OS)
- **Not suitable for precise fMRI BOLD time-locking**.
  For fMRI, use `Grammaticality_RWL_fMRI.py` (Pygame, ~1 ms precision).
- **Suitable for**: behavioral pilots, item difficulty estimation, remote
  participant testing, demo/teaching.

## Output Files

When experiment completes, two CSV files can be downloaded:

### `sub-{ID}_form-{A|B}_{timestamp}_results.csv`

Per-trial data (columns):
- `run`, `trial`, `item_id`, `pair_id`, `version`, `item_type`
- `family_id`, `construct`, `q_vector`
- `prime_text`, `target_text`, `target_lemma`, `critical_region`
- `expected_response`, `response`, `response_correct`
- `rt_from_target_onset_ms`, `iti_ms`
- `time`, `onset_from_session_s`, `list_form`

### `sub-{ID}_form-{A|B}_{timestamp}_key_events.csv`

Every keypress / button click (columns):
- `run`, `trial`, `item_id`, `phase`
- `key_name`, `key_label`, `key_source`
- `normalized_response`, `phase_time_ms`
- `time`, `onset_from_trigger_s`

## Local Development

### Edit and reload

```bash
# Edit experiment.js, then refresh browser
# No build step needed
```

### Debugging

Open browser DevTools (F12) → Console for `console.log` output.

Key state object is in closure but you can inspect via:
- `localStorage` (if persistence is added later)
- Network tab → check `stimuli.json` and audio file requests
- Application tab → see audio cache

### Adjusting timings

Edit `TIMING` object at the top of `experiment.js`, or use the
**詳細設定** (Advanced) section in the setup form to override at runtime.

## Limitations vs Pygame fMRI Version

| Feature | Pygame | Web Static |
|---|---|---|
| Timing precision | ~1 ms | ~10-50 ms |
| fMRI trigger | physical `5` key | manual button click |
| Result file save | local FS via Python | browser download |
| Audio sync | precise (pygame.mixer) | best-effort (HTMLAudioElement) |
| Offline use | yes | yes (after first load) |
| Multi-participant | local per-script | URL-shareable for remote pilots |
| Pre-load all stimuli | yes | yes (cached after first run) |
| Best use case | fMRI scanner | behavioral pilot / demo |

## License

Use is restricted to the original research project unless explicitly granted.

## Citation

If you use this stimulus bank or task in your research, please cite:
- [TBD: project citation]
