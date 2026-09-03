"""
build_manual.py
Builds docs/BioSuite-NG_User_Manual.pdf -- a complete illustrated user
guide, using real screenshots of the running app (docs/manual_screens/).
Run once from the project root: `python build_manual.py`
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, KeepTogether
)

ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENS = os.path.join(ROOT, "docs", "manual_screens")
LOGO = os.path.join(ROOT, "assets", "logo_square.png")
OUT = os.path.join(ROOT, "docs", "BioSuite-NG_User_Manual.pdf")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=28, spaceAfter=6))
styles.add(ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=14, alignment=TA_CENTER,
                           textColor=colors.HexColor("#444444"), spaceAfter=4))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=17,
                           textColor=colors.HexColor("#1b2a4a"), spaceBefore=6, spaceAfter=8))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13,
                           textColor=colors.HexColor("#1b2a4a"), spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.3, leading=14.5))
styles.add(ParagraphStyle("Small", parent=styles["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#555555")))
styles.add(ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=10.3, leading=14.5,
                           textColor=colors.HexColor("#7a0000")))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5,
                           alignment=TA_CENTER, textColor=colors.HexColor("#666666"), spaceBefore=3))


def screenshot(filename, width_cm=16.5):
    path = os.path.join(SCREENS, filename)
    img = Image(path, width=width_cm * cm, height=width_cm * cm * 800 / 1150)
    img.hAlign = "CENTER"
    return img


def bullets(items, style=None):
    style = style or styles["Body"]
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=8) for t in items],
        bulletType="bullet", start="\u2022", leftIndent=14, spaceBefore=2, spaceAfter=6
    )


story = []

# ============================== COVER PAGE ============================== #
story.append(Spacer(1, 1.5 * cm))
if os.path.exists(LOGO):
    logo_img = Image(LOGO, width=4.2 * cm, height=4.2 * cm)
    logo_img.hAlign = "CENTER"
    story.append(logo_img)
story.append(Spacer(1, 0.8 * cm))
story.append(Paragraph("BioSuite-NG", styles["CoverTitle"]))
story[-1].alignment = TA_CENTER
story.append(Paragraph("User Manual", styles["CoverSub"]))
story.append(Paragraph("Radiobiological treatment-optimisation software", styles["CoverSub"]))
story.append(Spacer(1, 1.2 * cm))
story.append(HRFlowable(width="60%", thickness=0.8, color=colors.HexColor("#999999"), hAlign="CENTER"))
story.append(Spacer(1, 0.8 * cm))

cover_info = [
    "<b>Developed by:</b> Dr. Pouya Saraei (Saraei P.)",
    "<b>Affiliation:</b> Department of Medical Physics, Ahvaz Jundishapur "
    "University of Medical Sciences, Iran.",
    "<b>Based on the methodology of:</b> Uzan J, Nahum AE. Radiobiologically "
    "guided optimisation of the prescription dose and fractionation scheme "
    "in radiotherapy using BioSuite. <i>Br J Radiol.</i> 2012;85(1017):"
    "1279&ndash;1286. doi:10.1259/bjr/20476567",
]
for line in cover_info:
    p = Paragraph(line, styles["CoverSub"])
    p.alignment = TA_CENTER
    story.append(p)
    story.append(Spacer(1, 4))

story.append(PageBreak())

# ============================== DISCLAIMER ============================== #
story.append(Paragraph("DISCLAIMER", styles["H1"]))
story.append(Paragraph("IMPORTANT NOTES FOR USERS OF BIOSUITE-NG", styles["H2"]))
story.append(bullets([
    "Neither the developer nor Ahvaz Jundishapur University of Medical "
    "Sciences (AJUMS) can be held responsible for any issue that may arise "
    "from using this software for the treatment of patients.",
    "This program is <b>not destined for clinical use</b>.",
    "The final clinical decision should always lie with the clinician in "
    "charge of the case.",
], style=styles["Disclaimer"]))

story.append(Spacer(1, 10))
story.append(Paragraph(
    "BioSuite-NG is a research/educational reimplementation and extension "
    "of the BioSuite software described by Uzan &amp; Nahum (2012). All "
    "NTCP/TCP model parameters shown or shipped as defaults come from "
    "published literature fits to specific patient cohorts and carry the "
    "uncertainty inherent to those fits &mdash; this is discussed further "
    "in the Confidence Intervals section of this manual.",
    styles["Body"]
))
story.append(PageBreak())

# ============================== TABLE OF CONTENTS (manual) ============== #
story.append(Paragraph("Contents", styles["H1"]))
toc_items = [
    "1. Installation and launching the app",
    "2. Overall workflow",
    "3. Treatment plans tab",
    "4. Model/Endpoint parameters tab",
    "5. Adding endpoints from the LKB and TCP parameter banks",
    "6. DVH import tab",
    "7. DVH plots tab (TCP/NTCP, confidence intervals, sensitivity)",
    "8. Dose response curves tab",
    "9. Optimisation tab",
    "10. Fitting tab",
    "11. Export",
    "12. New features not in the original BioSuite",
    "13. Troubleshooting",
    "14. References",
]
story.append(bullets(toc_items))
story.append(PageBreak())

# ============================== 1. INSTALLATION ========================= #
story.append(Paragraph("1. Installation and launching the app", styles["H1"]))
story.append(Paragraph("Option A &mdash; one-click launcher (recommended)", styles["H2"]))
story.append(bullets([
    "Double-click <b>run_biosuitepy.bat</b>. The first run installs all "
    "required Python packages automatically (needs Python 3.10+ already "
    "installed on Windows); subsequent runs open faster.",
]))
story.append(Paragraph("Option B &mdash; standalone .exe (no Python needed afterwards)", styles["H2"]))
story.append(bullets([
    "Run <b>build_exe.bat</b> once. This produces <b>dist\\BioSuite-NG.exe</b>, "
    "which you can copy anywhere and double-click directly &mdash; no "
    "terminal, no Python install required on the target machine.",
    "If startup speed matters more than having a single file, run "
    "<b>build_exe_fast_start.bat</b> instead (produces a "
    "<b>dist\\BioSuite-NG\\</b> folder that starts faster on every launch "
    "&mdash; copy the whole folder, not just the .exe inside it).",
]))
story.append(Paragraph("Option C &mdash; manual command line", styles["H2"]))
story.append(bullets([
    "<font face='Courier'>pip install -r requirements.txt</font>",
    "<font face='Courier'>python main.py</font>",
]))
story.append(Paragraph("Why does it take a moment to open?", styles["H2"]))
story.append(Paragraph(
    "BioSuite-NG imports several large libraries at startup (PyQt6, "
    "matplotlib, scipy, pandas, and optionally pydicom) &mdash; typically "
    "2-5 seconds with a normal Python install. A --onefile .exe is slower "
    "still on its first launch because Windows has to unpack the bundled "
    "interpreter to a temporary folder before anything can run. To make "
    "sure you always get instant feedback that the app IS launching (and "
    "hasn't silently failed), a splash screen with the AJUMS logo appears "
    "immediately on double-click, before any of those slow imports happen.",
    styles["Body"]
))
story.append(PageBreak())

# ============================== 2. WORKFLOW ============================= #
story.append(Paragraph("2. Overall workflow", styles["H1"]))
story.append(Paragraph(
    "BioSuite-NG follows the same one-active-plan-at-a-time model as the "
    "original BioSuite: everything you do across every tab refers to the "
    "<b>current treatment plan</b> shown at the top of the window. The "
    "recommended order of work is:",
    styles["Body"]
))
story.append(bullets([
    "<b>Treatment plans</b> &mdash; create/select the plan (fractions, "
    "prescription dose, etc).",
    "<b>Model/Endpoint parameters</b> &mdash; define which NTCP/TCP models "
    "and parameters you will use (or load a saved/default bank).",
    "<b>DVH import</b> &mdash; load each structure's DVH and associate it "
    "with one of the endpoints you just defined.",
    "<b>DVH plots</b> &mdash; visually check the DVHs and read off TCP/NTCP, "
    "confidence intervals, and sensitivity.",
    "<b>Dose response curves</b> / <b>Optimisation</b> &mdash; explore dose "
    "escalation and find the isotoxic optimum.",
    "<b>Fitting</b> &mdash; (optional) calibrate the TCP model's &alpha; "
    "against your own cohort's clinical outcomes.",
]))
story.append(Paragraph(
    "Note this is why <b>Model/Endpoint parameters</b> comes before "
    "<b>DVH import</b> in the tab order: you need at least one endpoint "
    "defined before a DVH can usefully be associated with it.",
    styles["Small"]
))
story.append(PageBreak())


def tab_section(number, title, screenshot_file, intro, field_bullets, tips=None):
    story.append(Paragraph(f"{number}. {title}", styles["H1"]))
    story.append(Paragraph(intro, styles["Body"]))
    story.append(Spacer(1, 6))
    story.append(screenshot(screenshot_file))
    story.append(Paragraph(f"The {title.lower()} in BioSuite-NG.", styles["Caption"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("What each part does:", styles["H2"]))
    story.append(bullets(field_bullets))
    if tips:
        story.append(Paragraph("Tips:", styles["H2"]))
        story.append(bullets(tips))
    story.append(PageBreak())


# ============================== 3. TREATMENT PLANS ======================= #
tab_section(
    3, "Treatment plans tab", "01_treatment_plans.png",
    "This is where you create and manage treatment plans. A plan defines "
    "the prescription (fractions, dose, schedule) that every other tab "
    "will use for its calculations.",
    [
        "<b>Plan identifier</b> &mdash; a name you choose for this plan "
        "(e.g. patient ID or 'Patient3_Prostate').",
        "<b>Fractions</b> &mdash; total number of fractions.",
        "<b>Prescription dose (cGy)</b> &mdash; total physical dose.",
        "<b>Fraction(s)/day</b> and <b>Fractions/week</b> &mdash; schedule, "
        "used to compute overall treatment time (relevant for repopulation "
        "in the TCP model).",
        "<b>Add plan / Modify / Delete plan</b> &mdash; standard CRUD "
        "buttons; click a row in the table first to Modify or Delete it.",
    ],
)

# ============================== 4. MODEL/ENDPOINT ======================= #
tab_section(
    4, "Model/Endpoint parameters tab", "02_model_endpoint.png",
    "An <b>endpoint</b> pairs a clinical outcome (e.g. 'Rectum bleeding', "
    "'Prostate TCP') with a radiobiological model and its parameters. You "
    "define endpoints here BEFORE associating DVHs with them in the next tab.",
    [
        "<b>Add new endpoint</b> &mdash; opens a dialog where you choose "
        "NTCP or TCP, pick a model (LKB / Relative Seriality / SMD / EUD "
        "for NTCP; Marsden or LQ-SLR for TCP), and enter its parameters.",
        "<b>Add from LKB parameter bank [NEW]</b> / <b>Add from TCP "
        "parameter bank [NEW]</b> &mdash; pick a literature-sourced "
        "parameter set instead of typing values by hand; see the next "
        "section for both.",
        "<b>Delete endpoint</b> &mdash; click a row in the table to "
        "select it, THEN click Delete endpoint; it always removes "
        "whichever row is actually highlighted.",
        "<b>Load default bank</b> &mdash; loads <font face='Courier'>"
        "data/default_endpoints.json</font>, a starter set of organs "
        "(Lung, Rectum, Oesophagus) with literature parameters from the "
        "original paper's Table 1. Replace this file with your own "
        "parameter bank at any time.",
        "<b>Load list / Save list</b> &mdash; import/export your own set "
        "of endpoints as a JSON file, so you don't have to re-enter them "
        "every session.",
    ],
    tips=[
        "The summary table shows every parameter for every endpoint at a "
        "glance &mdash; use it to double check values before running "
        "calculations.",
    ],
)

# ============================== 5. LKB PARAMETER BANK ==================== #
story.append(Paragraph("5. Adding endpoints from the LKB and TCP parameter banks", styles["H1"]))
story.append(Paragraph("LKB parameter bank (NTCP)", styles["H2"]))
story.append(Paragraph(
    "Instead of typing LKB parameters in by hand, click <b>'Add from LKB "
    "parameter bank [NEW]'</b> in the Model/Endpoint parameters tab. This "
    "opens a curated, literature-sourced bank of <b>88 parameter sets "
    "across 51 organs</b>, built from a structured evidence review "
    "(classic Burman et al. 1991 values, QUANTEC-era updates, and newer "
    "conditional alternatives with full citations).",
    styles["Body"]
))
story.append(Spacer(1, 6))
story.append(screenshot("08_add_from_bank.png", width_cm=13.5))
story.append(Paragraph("The 'Add from LKB parameter bank' dialog.", styles["Caption"]))
story.append(Spacer(1, 10))
story.append(Paragraph("What each part does:", styles["H2"]))
story.append(bullets([
    "<b>Organ \u2192 Endpoint \u2192 Parameter set (author, year)</b> "
    "&mdash; three cascading dropdowns, all searchable-as-you-type "
    "[NEW] (type e.g. \"rect\" to jump straight to Rectum, case-"
    "insensitive, matches anywhere in the name). Some organ/endpoint "
    "combinations have more than one citable parameter set (e.g. a "
    "historical Burman 1991 value AND a newer conditional alternative) "
    "&mdash; pick whichever matches your case by its \u201cAuthor et al. "
    "Year\u201d label.",
    "<b>Detail panel</b> &mdash; shows n, m, TD50, the reference volume, "
    "the dose reference (physical / EQD2 / EQD25 / Gy(RBE) &mdash; these "
    "are NOT interchangeable), the evidence status, and the full citation.",
    "<b>alpha/beta warning</b> &mdash; the LKB model itself only has three "
    "parameters (TD50, m, n); alpha/beta is only needed for fractionation "
    "(EQD2) correction. When the source paper did not report one, "
    "BioSuite-NG shows a red warning and <b>requires</b> you to type a "
    "value in before the endpoint can be added &mdash; it is never "
    "silently guessed for you.",
]))
story.append(Paragraph("Tips:", styles["H2"]))
story.append(bullets([
    "Open <b>Radiobiology \u2192 'LKB parameter bank (methodology &amp; "
    "references)'</b> at any time for the full methodology, the meaning "
    "of every evidence-status label, and the primary references &mdash; "
    "this is what lets you double-check a parameter set before trusting it.",
    "A 2023 systematic review found over 500 different published LKB "
    "parameter sets with substantial disagreement between them &mdash; "
    "always sanity-check a bank entry against your own institution's "
    "experience before using it to inform a real decision.",
]))
story.append(PageBreak())

# ------------------------------ TCP parameter bank ------------------------ #
story.append(Paragraph("TCP parameter bank", styles["H2"]))
story.append(Paragraph(
    "The same idea, for tumour control: click <b>'Add from TCP parameter "
    "bank [NEW]'</b> in the Model/Endpoint parameters tab to pick from "
    "<b>14 Target/Poisson TCP parameter sets across 9 tumour sites</b> "
    "(lung, prostate, cervix, bladder, breast, CNS, liver, oesophagus, "
    "rectum).",
    styles["Body"]
))
story.append(Spacer(1, 6))
story.append(screenshot("09_add_tcp_from_bank.png", width_cm=13.5))
story.append(Paragraph("The 'Add from TCP parameter bank' dialog.", styles["Caption"]))
story.append(Spacer(1, 10))
story.append(Paragraph("What each part does:", styles["H2"]))
story.append(bullets([
    "<b>Tumour site \u2192 Endpoint \u2192 Parameter set</b> &mdash; same "
    "cascading, searchable-as-you-type pattern as the LKB bank.",
    "<b>Model family</b> &mdash; only records BioSuite-NG's engine can "
    "actually reproduce are selectable: <i>computable_full</i> (matches "
    "the Marsden engine directly) or <i>alpha_beta_evidence_only</i> "
    "(the source reports ONLY alpha/alpha-beta -- you must supply "
    "density, spread and repopulation yourself). Records using an "
    "incompatible formalism (e.g. Zaider-Minerbo re-sensitisation) are "
    "documented in the bank but not offered here.",
    "<b>Total clonogens K vs. density &mdash; the single most important "
    "rule in this bank:</b> some sources report an absolute clonogen "
    "COUNT (K) for their cohort, not a per-cc density, and explicitly "
    "state it must NOT be divided by an arbitrary volume. When that's "
    "the case, BioSuite-NG uses K exactly as reported, for ANY structure "
    "the endpoint is later applied to -- the 'GTV volume' field will NOT "
    "change the result for those records (this is intentional, not a "
    "bug: an earlier version of this dialog let K be divided by a "
    "typed-in volume, which silently contradicted the source's own "
    "caveat and could produce a misleadingly-small TCP).",
    "Any field the record doesn't report (alpha spread, density/K, "
    "repopulation timing) appears as a required input below the detail "
    "panel &mdash; nothing is silently defaulted.",
]))
story.append(Paragraph("Tips:", styles["H2"]))
story.append(bullets([
    "Open <b>Radiobiology \u2192 'TCP parameter bank (methodology &amp; "
    "references)'</b> for the full methodology and the K-vs-density rule "
    "in detail.",
    "TCP models assume the DVH represents an actual tumour target "
    "receiving a full course of treatment. Applying a tumour's clonogen "
    "count to a normal-tissue/OAR DVH (or to a DVH with a cold spot, i.e. "
    "some volume at/near zero dose) will correctly predict TCP near 0% "
    "-- see the DVH plots tab's TCP tooltip for a live explanation when "
    "this happens.",
]))
story.append(PageBreak())

# ============================== 6. DVH IMPORT ============================ #
tab_section(
    6, "DVH import tab", "03_dvh_import.png",
    "Load each structure's dose-volume histogram (DVH) here, and link "
    "(associate) it to one of the endpoints you defined in the previous tab.",
    [
        "<b>Load DVH</b> &mdash; opens a file picker accepting Excel "
        "(native Pinnacle export format, or generic wide/long layout) or "
        "CSV files.",
        "<b>Load Eclipse/DICOM DVH</b> &mdash; imports directly from a "
        "DICOM RTDOSE + RTSTRUCT pair (no manual export needed).",
        "<b>Accumulate DVHs (4D) [NEW]</b> &mdash; select two or more "
        "DVHs of the SAME structure (e.g. different breathing phases, or "
        "primary course + boost) and combine them into one accumulated DVH.",
        "<b>Associated organ/endpoint + Associate to DVH(s)</b> &mdash; "
        "select one or more DVH rows, pick an endpoint from the dropdown, "
        "and click Associate. This link is what lets the DVH plots, "
        "Optimisation, and Dose response curves tabs compute TCP/NTCP.",
        "<b>EUD (cGy) column</b> &mdash; the generalised EUD (Niemierko "
        "formula) computed on the EQD2-corrected DVH, using the volume "
        "exponent implied by the associated endpoint's model. If a DVH "
        "is not yet associated with an endpoint, this column falls back "
        "to the simple mean dose and is marked with an asterisk (*).",
    ],
    tips=[
        "You MUST associate a DVH with an endpoint before the DVH plots, "
        "Dose response curves, and Optimisation tabs will show any "
        "TCP/NTCP numbers for it.",
        "<b>Comparing the SAME structure under two different predictive "
        "parameter sets</b> (e.g. an OAR scored with both Author A's and "
        "Author B's LKB parameters): each endpoint-DVH link in "
        "BioSuite-NG is one fixed pairing, so load the SAME DVH file a "
        "SECOND time (Load DVH again, same file) to get a second, "
        "independent row for that structure, then associate that second "
        "copy with the second endpoint. You now have two rows -- same "
        "physical DVH, two different models/parameter sets -- and can "
        "compare their NTCP/TCP side by side in DVH plots or Optimisation. "
        "Repeat once per additional parameter set you want to compare.",
    ],
)

# ============================== 7. DVH PLOTS ============================= #
tab_section(
    7, "DVH plots tab", "04_dvh_plots.png",
    "The main visual/numerical check tab: plot any combination of "
    "structures' DVHs, and read off TCP/NTCP (with optional confidence "
    "intervals and sensitivity analysis) for the currently-selected structure.",
    [
        "<b>Structure list (checkboxes)</b> &mdash; tick/untick which "
        "DVHs are drawn on the chart; click a row to select it (this is "
        "what the TCP/NTCP boxes and CI/Tornado buttons act on).",
        "<b>TCP / LQ corrected NTCP boxes</b> &mdash; show the value for "
        "the currently-selected, endpoint-associated structure.",
        "<b>Compute 95% CI (Monte-Carlo) [NEW]</b> &mdash; propagates "
        "&plusmn;10% uncertainty on the model's key parameters through "
        "1000s of simulated NTCP calculations, reporting the resulting "
        "95% range. See Section 12 for how to interpret this.",
        "<b>Sensitivity (tornado) [NEW]</b> &mdash; opens a chart showing "
        "which single parameter drives the most uncertainty in NTCP.",
        "<b>Display options</b> &mdash; Normalised (chart title switches "
        "between 'Absolute value DVH(s)' and 'Normalized DVH(s)'), "
        "Differential/Cumulative DVH type, and Uncorrected/LQ-corrected "
        "dose display.",
    ],
    tips=[
        "The chart uses a fine graph-paper-style grid specifically so you "
        "can read off approximate values directly from the curve.",
    ],
)

# ============================== 8. DRC =================================== #
tab_section(
    8, "Dose response curves tab", "05_drc.png",
    "Reproduces Figures 1-2 of the original paper: shows how TCP/NTCP "
    "change as you escalate dose, either at a constant number of fractions "
    "(varying fraction size) or at a constant fraction size (varying the "
    "number of fractions).",
    [
        "<b>Constant... Fraction size / Fraction No.</b> &mdash; choose "
        "which quantity stays fixed while the other is swept.",
        "<b>Structure/endpoint list</b> &mdash; tick which associated "
        "structures appear on the chart.",
        "<b>Filter curves</b> &mdash; show TCPs only, NTCPs only, or both.",
        "<b>Max/Min frac.</b> &mdash; the fraction-number range to sweep "
        "when 'Fraction size' is held constant.",
        "<b>Compute curves</b> &mdash; runs the sweep and redraws the chart.",
    ],
)

# ============================== 9. OPTIMISATION =========================== #
tab_section(
    9, "Optimisation tab", "06_optimisation.png",
    "Reproduces Figures 3-5 of the original paper: the isotoxic 2D "
    "optimisation finds, for each number of fractions in a range, the "
    "highest total dose that keeps every associated NTCP endpoint at or "
    "below its limit, and plots the resulting TCP.",
    [
        "<b>Table</b> &mdash; every associated endpoint, its current "
        "value, and (for NTCP endpoints) an editable <b>Limit</b> column "
        "&mdash; set this to the maximum acceptable NTCP for that organ.",
        "<b>Change fraction range / overshoot limit</b> &mdash; controls "
        "the fraction-number search range and the TCP ceiling above which "
        "the optimiser stops escalating dose (green dots), vs. being "
        "genuinely NTCP-limited (red dots).",
        "<b>Run isotoxic optimisation</b> &mdash; executes the search and "
        "reports the best fraction number / total dose / TCP combination.",
    ],
    tips=[
        "You need exactly one TCP-kind endpoint associated for this tab "
        "to work; all NTCP-kind associated endpoints become simultaneous "
        "constraints.",
    ],
)

# ============================== 10. FITTING ================================ #
tab_section(
    10, "Fitting tab", "07_fitting.png",
    "The opposite direction from Optimisation: given real clinical outcome "
    "data (local control yes/no per patient), this tab fits the TCP "
    "model's &alpha; parameter by maximum likelihood, so the model matches "
    "YOUR patient cohort rather than only literature defaults.",
    [
        "<b>Add entry manually</b> &mdash; enter one patient's total dose, "
        "fractions, GTV volume, and outcome (1 = local control, 0 = failure).",
        "<b>Fill outcome</b> &mdash; bulk-set all entries' outcomes (useful "
        "for quick testing).",
        "<b>Model</b> &mdash; currently Marsden (LQ-Poisson) only.",
        "<b>Fitting equation</b> &mdash; ChiSq / Binomial / Bernoulli "
        "objective function for the fit.",
        "<b>Fit</b> &mdash; runs the fit and reports the fitted &alpha; "
        "and the resulting objective-function score in the Fit list.",
    ],
    tips=[
        "Only &alpha; is fitted; &alpha;/&beta;, &alpha;-spread and "
        "clonogen density are held fixed at the values in Model/Endpoint "
        "parameters. This matches how the original paper only varies "
        "&alpha;/tumour &alpha;/&beta; as a scenario, not a per-cohort fit.",
    ],
)

# ============================== 11. EXPORT ================================ #
story.append(Paragraph("11. Export", styles["H1"]))
story.append(Paragraph(
    "Reachable from <b>Radiobiology \u2192 Export...</b> at any time (not "
    "tied to a specific tab), this dialog gets data OUT of BioSuite-NG in "
    "plain CSV/JSON files you can open in Excel or any other tool.",
    styles["Body"]
))
story.append(bullets([
    "<b>NTCP/TCP summary for the active plan (CSV)</b> &mdash; one row per "
    "associated structure, with its endpoint, model, and computed "
    "NTCP/TCP value.",
    "<b>Raw DVH data for the active plan's structures (CSV)</b> &mdash; "
    "every dose bin of every loaded structure, long-format "
    "(Structure, Dose_cGy, Volume_cm3).",
    "<b>Endpoint list (JSON)</b> &mdash; identical format to Model/Endpoint "
    "parameters' 'Save list', so you can archive or share exactly which "
    "endpoints/parameters were used for a given analysis.",
]))
story.append(PageBreak())

# ============================== 12. NEW FEATURES ========================== #
story.append(Paragraph("12. New features not in the original BioSuite", styles["H1"]))
story.append(Paragraph(
    "BioSuite-NG adds several capabilities the original 2012 BioSuite did "
    "not have. The table below summarises where each lives and what it's for.",
    styles["Body"]
))
story.append(Spacer(1, 8))

feature_rows_raw = [
    ["Feature", "Where", "What it's for"],
    ["EUD/Niemierko NTCP model", "Model/Endpoint parameters (Model = 'EUD')",
     "An additional NTCP model option beyond LKB/RS/SMD."],
    ["Monte-Carlo 95% CI", "DVH plots \u2192 'Compute 95% CI' button",
     "Shows how much NTCP could plausibly vary given \u00b110% "
     "uncertainty on the model's own parameters. Wired up for LKB, RS, "
     "SMD and EUD models."],
    ["Sensitivity (tornado)", "DVH plots \u2192 'Sensitivity (tornado)' button",
     "Shows WHICH single parameter drives the most NTCP uncertainty."],
    ["4D dose accumulation", "DVH import \u2192 'Accumulate DVHs (4D)' button",
     "Combines 2+ DVHs of the same structure (breathing phases, or "
     "primary+boost courses) into one accumulated DVH."],
    ["DICOM-RT import", "DVH import \u2192 'Load Eclipse/DICOM DVH' button",
     "Reads DVHs directly from RTDOSE+RTSTRUCT files."],
    ["Pinnacle/Excel import", "DVH import \u2192 'Load DVH' button",
     "Auto-detects and reads the native Pinnacle DVH export block format, "
     "or generic wide/long Excel layouts."],
    ["LKB parameter bank", "Model/Endpoint parameters \u2192 'Add from LKB "
     "parameter bank'; docs at Radiobiology \u2192 'LKB parameter bank'",
     "88 literature-sourced LKB parameter sets across 51 organs, with "
     "multiple citable options per endpoint and mandatory alpha/beta "
     "entry when a source didn't report one."],
    ["TCP parameter bank", "Model/Endpoint parameters \u2192 'Add from TCP "
     "parameter bank'; docs at Radiobiology \u2192 'TCP parameter bank'",
     "14 Target/Poisson TCP parameter sets across 9 tumour sites, with "
     "strict separation between total clonogen count (K) and per-cc "
     "density so the two are never silently confused."],
    ["Searchable dropdowns", "Organ/Endpoint/Site fields in both parameter "
     "banks", "Type any part of a name (case-insensitive) to filter "
     "instantly, e.g. \"rect\" jumps straight to \"Rectum\"."],
    ["Export", "Radiobiology \u2192 'Export...'",
     "Get DVH data, NTCP/TCP summaries, or the endpoint list out as "
     "CSV/JSON files."],
    ["Splash screen", "Shown automatically on launch",
     "Instant visual confirmation the app is starting, before the slower "
     "library imports happen."],
]
cell_style = ParagraphStyle("Cell", parent=styles["Small"], fontSize=8.3, leading=10.5,
                             textColor=colors.black)
header_style = ParagraphStyle("CellHeader", parent=cell_style, textColor=colors.white,
                               fontName="Helvetica-Bold")
feature_rows = []
for r_idx, row in enumerate(feature_rows_raw):
    style = header_style if r_idx == 0 else cell_style
    feature_rows.append([Paragraph(cell, style) for cell in row])

tbl = Table(feature_rows, colWidths=[3.4 * cm, 4.6 * cm, 8.2 * cm], repeatRows=1)
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a4a")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
]))
story.append(tbl)

story.append(Spacer(1, 14))
story.append(Paragraph("Interpreting the confidence interval", styles["H2"]))
story.append(Paragraph(
    "The original paper explicitly lists the absence of confidence "
    "intervals as a limitation of BioSuite (\u201cIn its current state, "
    "BioSuite does not include any confidence interval calculations on "
    "NTCP and TCP...\u201d). BioSuite-NG's Monte-Carlo CI fills that gap "
    "by sampling the model's own parameters (e.g. TD50 and m for LKB) "
    "from a normal distribution and recomputing NTCP thousands of times.",
    styles["Body"]
))
story.append(Paragraph(
    "<b>Important caveat:</b> the \u00b110% standard deviation used for "
    "every parameter is currently a generic placeholder, not a value "
    "derived from the literature source of each specific parameter set. "
    "Treat the resulting interval as illustrative of how sensitive the "
    "result is to parameter uncertainty in general, not as a "
    "publication-ready statistical confidence interval, until the "
    "placeholder is replaced with real reported standard errors.",
    styles["Small"]
))
story.append(PageBreak())

# ============================== 13. TROUBLESHOOTING ======================= #
story.append(Paragraph("13. Troubleshooting", styles["H1"]))
story.append(bullets([
    "<b>\u201cNo NTCP/TCP shows up in DVH plots\u201d</b> &mdash; make sure "
    "you associated the structure's DVH with an endpoint in the DVH "
    "import tab (select the row, choose an endpoint, click 'Associate to "
    "DVH(s)'), and that the structure's row is selected/highlighted in "
    "the DVH plots tab's list.",
    "<b>\u201cCompute 95% CI\u201d says a model isn't wired up</b> &mdash; "
    "this currently covers LKB, RS, SMD and EUD NTCP models; TCP-endpoint "
    "CI is not yet implemented.",
    "<b>Chart looks squashed on a small window</b> &mdash; resize the "
    "window taller; the charts reserve fixed margins so axis labels are "
    "never clipped, but very small windows will still compress the plot area.",
    "<b>DICOM-RT import fails</b> &mdash; confirm both an RTDOSE and an "
    "RTSTRUCT file from the SAME plan/study are selected, and that the "
    "structure name you type matches the ROI name exactly as stored in "
    "the RTSTRUCT file.",
    "<b>\u201cAdd from LKB parameter bank\u201d won't let me click OK</b> "
    "&mdash; the chosen parameter set's source did not report alpha/beta; "
    "type a value into the 'alpha/beta (Gy) to use' field first (see "
    "Section 5). This is deliberate: BioSuite-NG never invents a "
    "fractionation-correction value on your behalf.",
]))
story.append(PageBreak())

# ============================== 14. REFERENCES ============================ #
story.append(Paragraph("14. References", styles["H1"]))
story.append(Paragraph(
    "Uzan J, Nahum AE. Radiobiologically guided optimisation of the "
    "prescription dose and fractionation scheme in radiotherapy using "
    "BioSuite. <i>Br J Radiol.</i> 2012;85(1017):1279&ndash;1286. "
    "doi:10.1259/bjr/20476567",
    styles["Body"]
))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "See the project's README.md for the full list of model-parameter "
    "literature sources (Seppenwoolde et al., Rancati et al., Bentzen et "
    "al., Nahum et al., etc.) reproduced from the original paper's "
    "Tables 1 and 2.",
    styles["Small"]
))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "The original BioSuite's own exercise sheet (\u201cBIOSUITE EXERCISES "
    "SHEET\u201d, CCO/J. Uzan, 2012) was also used directly to cross-check "
    "BioSuite-NG's engine: it confirmed the Relative Seriality model "
    "gives an NTCP close to the LKB model for the same lung endpoint "
    "(the exercise sheet's own worked example), and that the Simple "
    "Maximum Dose model is an essentially binary (0%/100%) sigmoid at "
    "realistic cGy-scale doses -- both reproduced exactly by "
    "BioSuite-NG's implementation.",
    styles["Small"]
))

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    title="BioSuite-NG User Manual", author="Dr. Pouya Saraei",
)
doc.build(story)
print("Wrote", OUT)
