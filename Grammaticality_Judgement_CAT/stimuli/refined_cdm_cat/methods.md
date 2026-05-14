# Methods — CDM/CAT v3 Stimulus Bank

## 1. Research Question

How does the brain of L1 Japanese B1-B2 English learners process English countability grammar (mass/count distinctions, articles, plural marking, quantifier selection, fixed noncount, plural-only) under reading-while-listening (RWL) conditions?

**Primary hypothesis**: BOLD response in language-processing regions (LIFG, LMTG, anterior temporal) will differ across grammatical-violation types, with a specific 2×2 dissociation of concreteness (concrete vs abstract) × grammar (count vs mass).

## 2. Stimulus Bank Overview

- **Total items**: 216 (168 critical + 48 fillers)
- **Critical pairs**: 84 (G/U pairs across 14 word families, 6 pairs each)
- **Fillers**: 48 (24 G_filler grammatical + semantically odd, 24 U_filler ungrammatical + plausible)
- **Format**: prime sentence (7-8 words) + target sentence (5 words for G/U)
- **Presentation**: Reading-While-Listening (RWL) with synchronized text + TTS audio

## 3. Word Family Taxonomy

| WF | Name | Construct (G vs U) | q-vector |
|---|---|---|---|
| F01 | singular_count_missing_article | "a lamp" vs "lamp" (article omission) | 001000 |
| F02 | indefinite_article_a_an | "an orange" vs "a orange" (allomorph) | 001000 |
| F03 | count_noun_plural_after_numeral | "five apples" vs "five apple" | 000100 |
| F04 | mass_noun_many_much | "much knowledge" vs "many knowledge" (abstract) | 100010 |
| F05 | count_noun_many_much | "many books" vs "much books" | 100010 |
| F06 | noncount_indefinite_article | "some advice" vs "a advice" (abstract mass) | 101000 |
| F07 | noncount_plural_error | "music" vs "musics" (mass + -s) | 100100 |
| F08 | count_to_mass_food_context | "too much carrot" vs "too many carrot" (coerced mass) | 110010 |
| F09 | mass_to_serving_count | "three coffees" vs "three coffee" (mass→serving) | 110100 |
| F10 | mass_to_kind_count | "These wines" vs "These wine" (mass→kind) | 110100 |
| F11 | fixed_noncount_plural_error | "furniture" vs "furnitures" (fixed mass + -s) | 000101 |
| F12 | plural_only_pair_nouns | "These jeans" vs "This jeans" (plurale tantum) | 000101 |
| **F13** | **concrete_mass_many_much** | **"much plastic" vs "many plastic" (concrete mass)** | **100010** |
| **F14** | **abstract_count_plural_after_numeral** | **"three topics" vs "three topic" (abstract count)** | **000100** |

F13 and F14 are dissociation families introduced to create a clean 2×2 design with F04 and F03.

## 4. 2×2 Concreteness × Count/Mass Design

```
                Concrete (≈4.8-5.0)    Abstract (≈2.3-2.6)
Count           F03 (n=6 pairs)        F14 (n=6 pairs)
Mass            F13 (n=6 pairs)        F04 (n=6 pairs)
```

This 4-cell ANOVA-equivalent structure allows isolating:
- Main effect of **concreteness** (F03+F13 vs F14+F04)
- Main effect of **count/mass grammar** (F03+F14 vs F13+F04)
- **Interaction** (whether concreteness modulates grammar processing)

## 5. Counterbalancing and Latin-Square

- **Two forms (A, B)** counterbalance G/U exposure
- For pairs P001-P042: G→Form A, U→Form B
- For pairs P043-P084: G→Form B, U→Form A
- Each participant sees **one form only** (84 critical items, one version per pair)
- Both forms see **all 48 fillers**
- Total per session: **132 items** (66 yes + 66 no, exact balance)

## 6. Run Structure (per form)

- **4 runs × ~33 trials × ~8 sec/trial** = ~22 min total task time
- Each WF appears in **all 4 runs** (1-2 items per run per WF)
- **Yes/no balanced per run** (16-17 of each)
- **No 3+ consecutive same-response trials** (rejection sampling constraint)

## 7. Trial Timing

| Stage | Duration |
|---|---|
| Fixation cross | 500 ms |
| Prime (text + audio synchronized) | up to 3500 ms |
| Pause | 500 ms |
| Target (text + audio synchronized) | up to 2500 ms |
| Response window (after audio offset) | up to 2000 ms |
| ITI (jittered) | 500-2500 ms (mean 1500) |
| **Trial total** | **~8000 ms mean** |

## 8. Audio Generation Specifications

**Recommended TTS**: Amazon Polly Joanna (Neural) — supports SSML phoneme override (critical for F02).

Alternative: OpenAI tts-1 nova, with manual audio splicing for F02 U items.

### F02 a/an Override Protocol (mandatory)

Six U items must preserve the orthographic "a + vowel-initial noun" violation. TTS systems may auto-coarticulate to "/ən/", destroying the violation. Use SSML:

```xml
<speak>
  Sara ate <phoneme alphabet="ipa" ph="ə">a</phoneme> orange quickly.
</speak>
```

Apply to all 6 F02 U items: P007U, P008U, P009U, P010U, P011U, P012U.

### F01 U Audio Padding (recommended)

F01 U targets are 4 words (vs 5 for G), creating a ~370 ms audio asymmetry. Pad U audio files with **370 ms trailing silence** to equate total target-epoch duration.

Affects: P001U, P002U, P003U, P004U, P005U, P006U.

### Forced Alignment (required for fMRI)

After TTS generation, run forced alignment (Gentle / Montreal Forced Aligner / whisperX) on each target audio. Extract:
- Per-word onset (ms from audio start)
- Per-word duration

Use the **critical-region word onset** as the GLM event time (not trial onset). This is critical for time-locking BOLD response to the violation.

Add column `critical_word_onset_ms_aligned` to the master CSV.

## 9. Covariate Columns (CSV)

| Column | Purpose |
|---|---|
| target_word_count | Length covariate (F01 dW=+1) |
| target_char_count | Visual length |
| prime_word_count | Prime length |
| lemma_letters, lemma_syllables | Lemma surface properties |
| zipf_wordfreq | Lexical frequency (wordfreq large EN) |
| cefr_j_level | A1/A2/B1/B2 estimate from Zipf |
| aoa_kuperman | Age of acquisition (Kuperman 2012 approx) |
| concreteness | Brysbaert 2014 approximation (1-5) |
| katakana_cognate | 0=none, 1=weak, 2=strong (manual) |
| gairaigo_mismatch | 1 if false friend (manual) |
| dual_violation_flag | 1 for F08 (count→mass coercion has dual violation) |
| audio_duration_ms_est | Pre-recording estimate |
| critical_region | Text of violation region |
| critical_region_word_pos | 1-indexed word position |

## 10. Pre-registered A Priori Contrasts

To control multiple comparisons, pre-register the following primary contrasts:

### Primary contrasts (n=5)
1. **2×2 main: concreteness** — (F03+F13) vs (F14+F04)
2. **2×2 main: count/mass** — (F03+F14) vs (F13+F04)
3. **2×2 interaction** — F03−F14 vs F13−F04
4. **G vs U (overall ungrammaticality)** — all G vs all U
5. **Coercion vs default** — (F08+F09+F10) vs (F03+F05+F12)

### Secondary contrasts (n=5)
6. Article violations (F01+F02+F06) vs other
7. Plural-marking violations (F03+F07+F11+F14) vs other
8. Quantifier violations (F04+F05+F08+F13) vs other
9. Critical-region effect: violation onset vs baseline
10. Cognate × violation: katakana_cognate × G/U interaction

### Exploratory (no correction)
- Per-WF contrasts (14 individual)
- Latency × accuracy correlation
- Individual difference moderators

## 11. Expected Difficulty Per WF

Based on construct difficulty and JP L1 transfer:

| WF | Expected detection rate |
|---|---|
| F02 a/an | ~85% (phonologically salient) |
| F05 count many/much | ~80% (drilled in JHS) |
| F04 mass many/much | ~80% (drilled) |
| F03 count plural | ~80% (drilled) |
| F08 count→mass | ~60% (depends on coercion success) |
| F01 article omission | **~50%** (no JP analog) |
| F09 mass→serving | ~55% (coercion test) |
| F07 mass + plural | ~60% (drilled in JHS) |
| F13 concrete mass | ~70% (mirror F04) |
| F14 abstract count | ~75% (mirror F03) |
| F06 mass + a/an | ~55% (subtle) |
| F11 fixed mass + plural | ~50% (often produced by learners) |
| F10 mass→kind | **~40%** (subtle coercion) |
| F12 plurale tantum | **~30-40%** (katakana count-pattern transfer) |

F01, F10, F12 are pre-registered as **expected high-difficulty** WFs.

## 12. Analysis Plan

### Behavioral
- Per-WF mean accuracy (G correct / U correct)
- Per-WF mean RT (correct trials only)
- d′ per WF
- Covariate-adjusted accuracy: GLM with predictors {Zipf, AoA, concreteness, cognate, dual_violation, length}

### fMRI
- **GLM**: critical-word onset as event time (from forced alignment)
- **Regressors**: 
  - Main: WF × (G vs U)
  - Nuisance: target_word_count, lemma_zipf, AoA, concreteness, katakana_cognate, run, motion
- **Contrasts**: 5 primary + 5 secondary (above), FDR-corrected within each tier
- **ROIs**: Language network (LIFG IFGtri, LIFG IFGop, LMTG, LSTG, LAntT, LAngG), Multiple Demand network (control)
- **Whole-brain**: voxel-wise FWE p<0.05 cluster correction

## 13. Bank Versioning History

- **v1**: 12 word families, 100 stimuli (legacy, pre-CDM/CAT)
- **v1 CDM/CAT**: 144 items, identified concreteness×grammar confound, F10 prime leakage, Q-matrix issues
- **v2**: 12 word families × 12 items = 144 items, post-audit revisions
- **v3 (this version)**: 14 word families × 12 critical + 48 fillers = 216 items
  - Added F13 (concrete mass) + F14 (abstract count) for 2×2 design
  - All B2+/C1 vocab in primes/targets removed
  - Name distribution rebalanced to 50F/50M, 5-6 each
  - Adverb diversity expanded (today/yesterday capped at 6)
  - F06 lemmas replaced (kindness/wisdom/anger/sadness → information/evidence/feedback→guidance/leisure)
  - F08 lemmas replaced (chicken/pepper/garlic → strawberry/cabbage/blueberry)
  - F10 lemmas replaced (bread/chocolate/butter → vinegar/honey/jam)
  - F07 mail → scenery; F11 software → footwear

## 14. Known Limitations / Receivable Trade-offs

1. **F01 dW=+1**: article omission inherently creates 1-word length difference. Modelled via target_word_count covariate.
2. **F08 dual violation**: "too many carrot" has both quantifier-noun mismatch + plural-marker omission. Modelled via dual_violation_flag.
3. **F12 katakana effect**: JP loanwords ジーンズ/ショーツ behave as count-singular, expected high-difficulty.
4. **Cognate × WF confound**: F08 (strawberry, tomato, blueberry) and F12 (jeans, sunglasses, etc.) have high cognate density. Modelled via katakana_cognate covariate.
5. **Critical-region position × WF**: each WF has a deterministic critical-word position. Addressed by audio-onset time-locking in GLM.
6. **Filler items lack `target_lemma`**: by design (fillers don't test specific lemmas). Analysis pipeline must handle.

## 15. Files

- `stimulus_master_cdm_cat_v3.csv` — master CSV (216 rows × 38 cols)
- `_v2_draft_72pairs.csv` — intermediate draft (pre-v3)
- `_v3_draft_72pairs.csv` — intermediate draft (post-vocab fix)
- `_v3_draft_84pairs.csv` — intermediate draft (post-Batch 5)
- `_v3_draft_48fillers.csv` — filler subset
- `f02_ssml_script.py` — SSML generation helper for F02 audio (separate file)
- `pilot_protocol.md` — behavioral pilot procedure (separate file)
