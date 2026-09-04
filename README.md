# BioSuite-NG

Python reimplementation + extension of **BioSuite** (Uzan & Nahum, *Br J
Radiol* 2012;85:1279-1286) -- a radiobiological treatment-optimisation tool
computing NTCP/TCP and suggesting optimal prescription dose / fractionation.
For more detailed information, please refer to the *BioSuite-NG User Manual*.

**Developed by:** Dr. Pouya Saraei (Saraei P.)
**Affiliation:** Department of Medical Physics, Ahvaz Jundishapur University
of Medical Sciences, Iran.
**Based on the original methodology of:** Uzan J, Nahum AE. *Radiobiologically
guided optimisation of the prescription dose and fractionation scheme in
radiotherapy using BioSuite.* Br J Radiol. 2012;85:1279-1286.
doi:10.1259/bjr/20476567

## DISCLAIMER

This program is **not destined for clinical use**. Neither the developer
nor Ahvaz Jundishapur University of Medical Sciences (AJUMS) can be held
responsible for any issue arising from using this software for the
treatment of patients. The final clinical decision always lies with the
clinician in charge of the case.

## Status

Core engine + Windows desktop UI (PyQt6), both built and validated against
real patient data (3-patient Pinnacle export dataset) and cross-checked
against the original paper's own published numbers and the original
software's own exercise sheet.

## Validation highlights

- Rectum NTCP for the prostate patient at 74 Gy/37# comes out to **3.40%**,
  matching the paper's own stated value ("3.4% for 74 Gy per 37 fractions")
  almost exactly (`tests/test_real_patients.py`).
- The isotoxic optimisation correctly shows hypofractionation only becoming
  favourable for tumour alpha/beta <= 3 Gy, exactly as stated in the paper's
  Discussion.
- The NSCLC patients' relative TCP-NTCP separation (Patient 1 >> Patient 2)
  matches the paper's qualitative claim that Patient 1 has much more
  "escalation headroom" than Patient 2.
- Cross-checked against the original BioSuite's own exercise sheet
  ("BIOSUITE EXERCISES SHEET", CCO/J. Uzan, 2012): the Relative Seriality
  model gives an NTCP close to LKB for the same lung endpoint (as the
  exercise itself predicts), and the Simple Maximum Dose model is
  essentially a binary 0%/100% sigmoid at realistic cGy-scale doses --
  both reproduced exactly.

## How to run (Windows)

- **One click:** double-click `run_biosuitepy.bat` (installs dependencies
  automatically on first run).
- **Standalone .exe:** run `build_exe.bat` once to produce
  `dist\BioSuite-NG.exe` (uses PyInstaller's native `--splash` so the AJUMS
  logo appears instantly on double-click, before Python even starts). If
  startup speed matters more than a single file, use
  `build_exe_fast_start.bat` (`--onedir`) instead -- no unpack step at all.
- **Manual:**
  ```
  pip install -r requirements.txt
  python main.py
  ```

DICOM-RT DVH extraction uses only `pydicom` + `numpy` + `matplotlib` (already
required for everything else) -- no extra native/compiled dependency, and
no C++ Build Tools needed on Windows.

## What's implemented

### Core engine (`core/`, `dvh/`)

| Module | Contents |
|---|---|
| `core/tcp_models.py` | LQ-Poisson "Marsden" TCP (uniform-dose AND real-DVH versions) + accelerated repopulation; LQ-SLR (now fully wired, including the DVH-based `tcp_lq_slr_dvh`) |
| `core/ntcp_models.py` | LKB, Relative Seriality (Kallman), Simple Maximum Dose (SMD) |
| `core/ntcp_niemierko.py` | EUD-based NTCP (Niemierko/Luxton-Keall-King) |
| `core/dvh.py` | DVH data structure, EQD2 conversion, CSV import, DICOM-RT import |
| `core/optimizer.py` | 1D optimisation, 2D isotoxic optimisation (Fig. 3-5 of the paper) |
| `core/confidence.py` | Monte-Carlo confidence intervals + tornado sensitivity analysis on NTCP/TCP |
| `core/dose_accumulation.py` | DVH-level 4D dose accumulation |
| `core/fitting.py` | MLE fitting of TCP model's alpha to clinical outcome data (Bernoulli/Binomial/ChiSq) |
| `core/lkb_bank.py` | Loader for the 88-entry, 51-organ LKB (NTCP) parameter bank |
| `core/tcp_bank.py` | Loader for the 19-entry (14 directly computable), 9-tumour-site Target/Poisson TCP parameter bank |
| `core/paths.py` | Resolves bundled resource paths correctly in source AND PyInstaller-frozen runs |
| `dvh/excel_import.py` | Generic wide/long-format Excel DVH import |
| `dvh/pinnacle_excel_import.py` | Native Pinnacle "Points[]={...}" block-format Excel import |

### Desktop UI (`ui/`, PyQt6) 

1. **Treatment plans** -- add/modify/delete plans
2. **Model/Endpoint parameters** -- add NTCP/TCP endpoints manually, or from
   the LKB/TCP parameter banks; save/load endpoint lists as JSON
3. **DVH import** -- load DVH (Excel/Pinnacle/CSV) or DICOM-RT, accumulate
   multiple DVHs (4D), associate structures to endpoints
4. **DVH plots** -- differential/cumulative, normalised, LQ-corrected DVH
   plots with live TCP%/NTCP% readouts, Monte-Carlo CI, tornado sensitivity
5. **Dose response curves** -- constant-fraction-size or constant-fraction-
   number DRCs (reproducing Figs. 1-2 of the paper)
6. **Optimisation** -- 2D isotoxic optimisation with editable fraction
   range/overshoot limit (reproducing Figs. 3-5)
7. **Fitting** -- fit the TCP model's alpha to manually-entered clinical
   outcome data

Plus a **Radiobiology** menu with: About the models, LKB parameter bank
docs, TCP parameter bank docs, and Export (DVH data / NTCP-TCP summary /
endpoint list as CSV or JSON).

All tabs share one `AppState` object so data flows between them exactly as
in the original (one "current treatment plan" active across all tabs).

### Parameter banks

- **LKB (NTCP) bank** -- `data/lkb_parameter_bank.json`, built
  programmatically (not hand-typed) from `data/Radiobiological_TCP_NTCP.xlsx`,
  a structured, source-traceable evidence review, 88 parameter sets across
  51 organs, several endpoints with multiple citable alternatives (e.g.
  Burman et al. 1991 vs. a newer, alternative fit). Every record missing
  alpha/beta requires the user to supply one explicitly before use -- never
  guessed.
- **TCP bank** -- `data/tcp_parameter_bank.json`, built from the same
  evidence workbook, 19 Target/Poisson parameter sets across 9 tumour sites
  (14 directly computable with BioSuite-NG's engine; the rest kept for
  documentation/transparency only). Strictly separates "total clonogen
  count K" from "clonogen density per cc" -- these are NOT interchangeable,
  and a record reporting only K (with no source-defined reference volume)
  is applied as a FIXED total, decoupled from whatever GTV volume the user
  enters, per that source's own caveat.
- Both banks' dropdown fields (Organ/Site/Endpoint) are searchable-as-
  you-type, case-insensitive, matching anywhere in the name.

### Comparing one DVH under two different parameter sets

Each DVH-to-endpoint association in BioSuite-NG is a single fixed pairing.
To compare the SAME structure's DVH under two different predictive models
(e.g. Author A's vs. Author B's LKB parameters), load that DVH file a
SECOND time (DVH import -> Load DVH, same file again) and associate the
second copy with the second endpoint. You'll have two rows for the same
physical DVH, each showing a different model's prediction, comparable
side by side.

## Design notes / deviations from the original paper

- Root-finding uses `scipy.optimize.brentq`/`minimize_scalar` instead of
  the original's hand-rolled Brent implementation [ref 25].
- TCP for real (non-uniform) DVHs is computed by integrating survival
  fraction bin-by-bin over the differential PTV DVH, with total clonogen
  number fixed by the GTV volume -- exactly the method the paper describes
  in its NSCLC section ("TCPs are computed using the DVH of the PTV but
  this is assumed to contain the same number of clonogens as the
  corresponding GTV").
- `core/confidence.py`, `core/dose_accumulation.py`, `core/fitting.py`,
  `core/lkb_bank.py` and `core/tcp_bank.py` are new/extended capabilities
  not present in the original 2012 software.

## Acknowledgements

BioSuite-NG was developed by **Dr. Pouya Saraei**, Department of Medical
Physics, Ahvaz Jundishapur University of Medical Sciences, building on the
radiobiological modelling framework and validated methodology originally
described by Julien Uzan and Alan E. Nahum (Clatterbridge Cancer Centre)
in their 2012 paper introducing BioSuite. The TCP/NTCP model
implementations, dose-response methodology, and the isotoxic optimisation
approach in this project follow their published equations and parameter
tables; the extensions described above are new development on top of that
foundation.

> Uzan J, Nahum AE. Radiobiologically guided optimisation of the
> prescription dose and fractionation scheme in radiotherapy using
> BioSuite. *Br J Radiol.* 2012;85(1017):1279-1286.
> doi:10.1259/bjr/20476567
