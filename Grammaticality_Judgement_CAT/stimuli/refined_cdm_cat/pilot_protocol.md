# Behavioral Pilot Protocol

## Purpose

1. Verify item difficulty profiles before fMRI scanning
2. Identify items with floor (<25%) or ceiling (>95%) performance
3. Estimate per-WF mean accuracy and RT
4. Validate 2×2 concreteness × count/mass design via behavioral effects
5. Confirm B1-B2 accessibility of all lemmas and primes

## Participants

- **Target n**: 12-15 JP L1 English learners
- **Proficiency**: CEFR B1-B2 (verified via Eiken Pre-2/2 score, TOEIC L+R 500-790, or CELT)
- **Age**: 18-26 (university undergrad/grad equivalent)
- **Native language**: Japanese (no other L1 from age 0-12)
- **Other L2s**: none beyond classroom English

## Materials

- 132 items per participant = 1 form (A or B), counterbalanced
- TTS audio files (Polly Joanna or similar)
- Headphones for RWL audio delivery
- Visual: standard laptop screen (text 24pt centered, single line)

## Procedure

### Phase 1: Pre-task (5 min)
- Informed consent
- Proficiency verification (brief vocab test or Eiken score check)
- Equipment setup (headphones + screen calibration)
- 8 practice trials (4 G, 4 U; non-experimental items)
  - Feedback during practice
  - No feedback during main task

### Phase 2: Main task (~22 min)
- 4 runs × ~33 trials × ~8 sec/trial
- Self-paced 30 sec rest between runs
- Each trial:
  1. Fixation cross (500 ms)
  2. Prime: text + audio (up to 3500 ms)
  3. Pause (500 ms)
  4. Target: text + audio (up to 2500 ms)
  5. Response cue (up to 2000 ms): "Grammatical in this context?" "Yes/No"
  6. Inter-trial fixation (500-2500 ms jittered)

### Phase 3: Post-task (10 min)
- Brief debriefing questionnaire:
  - "Were any items unclear?" (list any vocabulary or constructions)
  - Self-rated difficulty per WF (1-5 Likert)
  - Strategy use (did you focus on grammar or meaning?)

## Measures

| Measure | Use |
|---|---|
| Per-WF accuracy (G correct / U correct) | Item difficulty estimate |
| Per-WF mean RT (correct trials, ms) | Processing-time profile |
| d′ per WF | Sensitivity index |
| Filler accuracy (G_filler yes-rate / U_filler no-rate) | Trap-detection rate |
| Lemma-level accuracy | Individual item exclusion candidates |

## Analysis

### Primary
- Per-WF accuracy means (target: 30-80%, exclude items <20% or >95%)
- 2×2 ANOVA on F03/F04/F13/F14 accuracy (concreteness × count/mass)
- 2×2 ANOVA on RT (correct trials)
- Trap-check: G_filler and U_filler accuracy as covariate

### Secondary
- Per-lemma exclusion candidates (extreme outliers in difficulty or RT)
- Cognate effect: katakana_cognate × accuracy correlation
- Family-cluster analysis (which WFs cluster on difficulty)
- Individual difference: proficiency × WF interaction

## Exclusion Criteria

### Participant-level
- G_filler accuracy < 75% (trap fail: rejecting odd-but-grammatical)
- U_filler accuracy < 75% (trap fail: accepting clear violations)
- Mean RT > 5000 ms (off-task)
- Self-report of unfamiliarity with >3 lemmas

### Item-level
- Accuracy < 20% (floor — too hard, likely vocabulary or construct unclear)
- Accuracy > 95% (ceiling — trivial)
- RT outlier: > 3 SD from item mean

## Pre-registered Predictions

| Prediction | Source |
|---|---|
| F02, F04, F05 highest accuracy (>75%) | JP textbook drill |
| F01, F10, F12 lowest accuracy (<50%) | No JP analog / cognate transfer |
| F03 vs F14 accuracy difference < 10% | 2×2 design predicts no concreteness main effect on count |
| F04 vs F13 accuracy difference < 10% | Same for mass |
| 2×2 interaction: count vs mass effect modulated by concreteness | Theoretical |
| Cognate (katakana=2) accuracy > non-cognate | Facilitation |

## Outcome Decisions

- If 0-3 items excluded: proceed to fMRI as-is
- If 4-10 items excluded: replace with reserve items (TBD) and re-pilot
- If >10 items excluded or 2×2 effect absent: review design with co-author

## Timeline

- Day 1-3: Recruit 12-15 participants
- Day 4-10: Run pilots (2-3 per day max)
- Day 11-12: Data analysis
- Day 13-14: Review and decide next steps
- Total: ~2 weeks

## Ethics

- Pre-approved IRB protocol (see IRB_Komuro_2025 folder)
- Compensation: 1000 yen / 30 min
- Data anonymized at collection (subject ID only)
