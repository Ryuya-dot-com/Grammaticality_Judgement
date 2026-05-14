# Pre-registration Template (OSF / AsPredicted)

## Title

Neural correlates of English countability grammar processing in L1 Japanese learners: A 2×2 fMRI design with reading-while-listening

## Hypotheses

### Primary hypothesis 1 (Concreteness × Count/Mass interaction)
The 2×2 design (F03/F04/F13/F14) will show an **interaction effect** in left inferior frontal gyrus (LIFG) BOLD response. Specifically, the difference between G and U items will be modulated by concreteness for mass nouns (F04 vs F13) more than for count nouns (F03 vs F14), reflecting differential demand on lexical-semantic retrieval during mass-coercion processing.

### Primary hypothesis 2 (Grammar violation effect)
All 14 WF G vs U contrasts will yield significant BOLD response in LIFG (BA44/45) and posterior middle temporal gyrus (pMTG), consistent with a syntactic-semantic violation network (Friederici, 2011; Hagoort, 2013).

### Primary hypothesis 3 (Family-level dissociation)
- Article violations (F01+F02+F06): peak in LIFG BA44 (formal syntax)
- Plural/number violations (F03+F07+F11+F14): peak in LMTG (lexical retrieval + agreement)
- Mass/count violations (F04+F05+F08+F13): peak in LAG/LIFG BA45 (semantic-pragmatic processing)
- Plurale tantum (F12): expected null or floor effect

### Secondary hypotheses
4. Detection accuracy will correlate with LIFG BA44 BOLD (higher detection → larger violation effect)
5. Katakana cognate items will show reduced LMTG activation (cognate facilitation)
6. F01 (article omission) will show effect even when length is covaried (genuine grammatical processing, not length detection)

## Participants

- **n target**: 30 (post-exclusion); recruit 35-40 to account for exclusions
- **Inclusion**: JP L1, CEFR B1-B2 (Eiken Pre-2 / 2, TOEIC L+R 500-790), right-handed, 18-26 yrs, normal/corrected vision, no neurological/psychiatric history
- **Exclusion**: behavioral G_filler accuracy <75%, U_filler accuracy <75%, fMRI motion >3mm

## Stimuli

- 132 items per participant (Latin square: Form A or Form B)
- 84 critical items + 48 fillers
- See `methods.md` for full specification

## Design

**Within-subject 2×2 ANOVA** within F03/F04/F13/F14 cells:
- Factor 1: concreteness (concrete: F03+F13; abstract: F14+F04)
- Factor 2: count/mass grammar (count: F03+F14; mass: F13+F04)

**Plus 14-way WF main effect** for whole-bank analysis.

## fMRI Protocol

- 3T Siemens Skyra/Prisma (Sophia Medical Center, [TO BE FILLED])
- T1 MPRAGE (5 min): 1mm³ iso, TR=2400ms, TE=2.22ms
- 4 task runs: 4.4 min each, multiband EPI (MB factor 4), TR=1000ms, TE=30ms, 2mm³ iso
- Optional: fieldmap (2 min), MD localizer (8 min)
- Total scan time: ~35-45 min

## Analysis Plan

### Preprocessing
- fMRIPrep v22+ (default settings)
- Motion correction, slice-timing, normalization to MNI152NLin2009cAsym
- AROMA + 24 motion parameters + 5 aCompCor as confounds

### GLM (1st-level, per participant)
- Event times: critical-word onset (from forced alignment); duration: critical-word duration
- Regressors: 14 WF × 2 (G/U) = 28 conditions
- Nuisance: target_word_count, lemma_zipf, AoA, concreteness, katakana_cognate, run, motion

### Contrasts (2nd-level)

**Primary (FDR-corrected within 5 contrasts, q<0.05):**
1. Concreteness main effect: (F03+F13) − (F14+F04)
2. Count/Mass main effect: (F03+F14) − (F13+F04)
3. 2×2 Interaction: (F03−F14) − (F13−F04)
4. G vs U (overall): all G vs all U
5. Coercion vs default: (F08+F09+F10) − (F03+F05+F12)

**Secondary (FDR within 5 contrasts):**
6. Article violations: (F01+F02+F06) U vs G − other
7. Plural violations: (F03+F07+F11+F14) U vs G − other
8. Quantifier violations: (F04+F05+F08+F13) U vs G − other
9. Critical-region onset effect (parametric)
10. Cognate × violation interaction

**Exploratory (uncorrected, descriptive):**
- 14 individual WF contrasts (G vs U)
- ROI: LIFG (BA44, BA45), LMTG, LAG, LSTG, LAntT

### Statistical thresholds
- Whole-brain: voxel p<0.001 uncorrected, cluster p<0.05 FWE (Worsley GRF)
- ROI: voxel p<0.05 FWE within ROI mask
- Effect size: Cohen's d > 0.5 for ROI

## Outcomes

### If hypotheses supported
- Submit findings to *Cerebral Cortex* / *NeuroImage* / *Journal of Cognitive Neuroscience*
- Preprint on bioRxiv simultaneously

### If hypotheses NOT supported
- Report null results in preprint
- Pre-register follow-up with revised design (e.g., higher proficiency learners, individual difference analysis)
- Share data openly

## Timeline

- Pre-registration submission: [DATE]
- Pilot data collection: [DATE]
- Pilot analysis: [DATE]
- fMRI acquisition: [DATE]
- Analysis: [DATE]
- Preprint submission: [DATE]

## Data Sharing

- Pre-registration: OSF (osf.io/[TBD])
- Stimulus bank: GitHub repo (open-access CC-BY-4.0)
- fMRI data: BIDS-formatted upload to OpenNeuro after publication
- Analysis code: GitHub (open-source MIT)

## Ethics and Consent

- IRB protocol approved (see `IRB_Komuro_2025/`)
- Compensation: 5000 yen for fMRI session
- Right to withdraw at any point
- Anonymized data only
