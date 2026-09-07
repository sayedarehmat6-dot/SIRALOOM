"""
annotations/report_v2.py
=========================
New report generator, structured against the published ESHG 2022
"Recommendations for reporting results of diagnostic genomic testing"
(Deans et al., Eur J Hum Genet 30:1011-1016), which explicitly aligns with
ACMG 2015 and UK-ACGS practice.

it: this pipeline produces a REANALYSIS CANDIDATE report — a supplementary
flag for physician review — not the certified diagnostic report of record.
That framing is printed on every page, not just mentioned in passing,
because burying it defeats the point of stating it honestly.

 
"""

from __future__ import annotations
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


def _p(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def _missing_field_note(value: Optional[str], field_name: str) -> str:
    return value if value else f"[{field_name} not provided]"


def generate_clinical_report(
    df: pd.DataFrame,
    buffer,
    # --- Administrative ---
    lab_name: str,
    lab_contact: str,
    report_authorized_date: Optional[str] = None,
    referring_physician: Optional[str] = None,
    referring_physician_address: Optional[str] = None,
    signatory_name: Optional[str] = None,
    signatory_role: Optional[str] = None,
    # --- Patient identification ---
    patient_full_name: Optional[str] = None,
    patient_dob: Optional[str] = None,
    patient_sex: Optional[str] = None,
    patient_id: Optional[str] = None,
    # --- Sample identification ---
    sample_id: Optional[str] = None,
    sample_type: Optional[str] = None,
    sample_collection_date: Optional[str] = None,
    sample_received_date: Optional[str] = None,
    # --- Restatement of clinical question ---
    clinical_indication: Optional[str] = None,
    test_type: str = "Reanalysis of previously unsolved case",
    referral_reason: Optional[str] = None,
    # --- Methods / provenance ---
    genome_build: str = "GRCh38",
    annotation_source: str = "GeneBe API",
    annotation_source_version: Optional[str] = None,
    acmg_engine_version: str = "ACMG-AMP 2015 (Richards et al.) — see methods note",
    include_technical_appendix: bool = True,
) -> None:
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.2 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, leading=10)
    header = ParagraphStyle("header", parent=styles["Heading2"])
    subheader = ParagraphStyle("subheader", parent=styles["Heading3"])
    box_style = ParagraphStyle("box", parent=normal, fontSize=13, leading=16,
                                textColor=colors.white, alignment=1)

    elements = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ---------------- Positioning banner — every page starts with this ----------------
    elements.append(Table(
        [[_p("<b>REANALYSIS CANDIDATE REPORT — SUPPLEMENTARY FINDING</b><br/>"
             "This is not a diagnostic report of record. It is intended to flag "
             "candidate findings for review by qualified laboratory personnel "
             "alongside the laboratory's own certified diagnostic pipeline.",
             box_style)]],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#7a1f1f")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]),
    ))
    elements.append(Spacer(1, 10))

    # ---------------- Administrative ----------------
    admin_html = (
        f"<b>{lab_name}</b> &nbsp;|&nbsp; {lab_contact}<br/>"
        f"Report authorized: {report_authorized_date or now_str}<br/>"
        f"Referring physician: {_missing_field_note(referring_physician, 'referring physician')}"
        + (f", {referring_physician_address}" if referring_physician_address else "")
    )
    elements.append(_p(admin_html, small))
    elements.append(Spacer(1, 8))

    # ---------------- Patient & sample identification ----------------
    id_html = (
        f"<b>Patient:</b> {_missing_field_note(patient_full_name, 'name')} &nbsp;&nbsp;"
        f"<b>DOB:</b> {_missing_field_note(patient_dob, 'DOB')} &nbsp;&nbsp;"
        f"<b>Sex:</b> {_missing_field_note(patient_sex, 'sex')} &nbsp;&nbsp;"
        f"<b>Patient ID:</b> {_missing_field_note(patient_id, 'patient ID')}<br/>"
        f"<b>Sample ID:</b> {_missing_field_note(sample_id, 'sample ID')} &nbsp;&nbsp;"
        f"<b>Sample type:</b> {_missing_field_note(sample_type, 'sample type')} &nbsp;&nbsp;"
        f"<b>Collected:</b> {_missing_field_note(sample_collection_date, 'collection date')} &nbsp;&nbsp;"
        f"<b>Received:</b> {_missing_field_note(sample_received_date, 'received date')}"
    )
    elements.append(_p(id_html, small))
    elements.append(Spacer(1, 8))

    # ---------------- Restatement of clinical question ----------------
    question_html = (
        f"<b>Clinical indication:</b> {_missing_field_note(clinical_indication, 'clinical indication')}<br/>"
        f"<b>Test type:</b> {test_type}<br/>"
        f"<b>Referral reason:</b> {_missing_field_note(referral_reason, 'referral reason')}"
    )
    elements.append(_p(question_html, small))
    elements.append(Spacer(1, 12))

    # ---------------- Headline conclusion ----------------
    df = df.copy().fillna("")
    reportable = df[~df["ACMG"].str.contains("benign", case=False, na=False)] if "ACMG" in df.columns else df
    pathogenic_rows = reportable[reportable["ACMG"].str.contains("pathogenic", case=False, na=False)] \
        if "ACMG" in reportable.columns else pd.DataFrame()

    if not pathogenic_rows.empty:
        genes = ", ".join(sorted(set(pathogenic_rows["GENE"].astype(str)))) if "GENE" in pathogenic_rows.columns else ""
        headline = f"CANDIDATE FINDING: {genes} — see classification detail below"
        headline_bg = "#1f4f2e"
    elif "ACMG" in reportable.columns and reportable["ACMG"].str.contains(
            "uncertain", case=False, na=False).any():
        headline = "VARIANT(S) OF UNCERTAIN SIGNIFICANCE — recorded for future re-review, not conclusive"
        headline_bg = "#7a6a1f"
    else:
        headline = "NO CLINICALLY SIGNIFICANT CANDIDATE FINDING IDENTIFIED ON REANALYSIS"
        headline_bg = "#2c2c2c"

    elements.append(Table(
        [[_p(f"<b>{headline}</b>", box_style)]],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(headline_bg)),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]),
    ))
    elements.append(Spacer(1, 14))

    # ---------------- Results table — P/LP/VUS only, benign excluded ----------------
    elements.append(_p("Candidate Variant(s)", header))
    elements.append(Spacer(1, 4))

    if reportable.empty:
        elements.append(_p("No candidate variants meeting reporting thresholds.", normal))
    else:
        cols = ["GENE", "HGVSc", "HGVSp", "CONSEQUENCE", "ACMG", "ClinVar"]
        cols = [c for c in cols if c in reportable.columns]
        header_row = [_p(f"<b>{c}</b>", small) for c in cols]
        data = [header_row]
        for _, r in reportable.iterrows():
            data.append([_p(str(r.get(c, "")), small) for c in cols])
        col_width = doc.width / max(1, len(cols))
        table = Table(data, colWidths=[col_width] * len(cols), repeatRows=1)
        tstyle = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#01579b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ])
        table.setStyle(tstyle)
        elements.append(table)
    elements.append(Spacer(1, 14))

    # ---------------- Interpretation ----------------
    elements.append(_p("Interpretation", header))
    interp_lines = []
    if not pathogenic_rows.empty:
        interp_lines.append(
            "The variant(s) above were flagged during automated reanalysis. "
            "Classification reflects either an established ClinVar precedent "
            "(multiple-submitter or expert-panel reviewed) or independently "
            "computed ACMG-AMP 2015 evidence where no such precedent exists. "
            "This finding should be independently reviewed and, if appropriate, "
            "confirmed via the laboratory's certified diagnostic pipeline before "
            "any clinical action is taken."
        )
        interp_lines.append(
            "If confirmed, this finding may have implications for other family "
            "members; genetic counselling is recommended."
        )
    else:
        interp_lines.append(
            "No candidate variant reached a reportable classification on this "
            "reanalysis pass. This does not exclude a genetic cause — reanalysis "
            "is inherently limited by current knowledge in reference databases "
            "and by the scope of evidence this pipeline can evaluate."
        )
    for line in interp_lines:
        elements.append(_p(line, normal))
        elements.append(Spacer(1, 6))

    elements.append(_p(
        "Reminder: genetic test results should be accompanied by genetic counselling.",
        ParagraphStyle("reminder", parent=normal, fontStyle="italic")
    ))
    elements.append(Spacer(1, 14))

    # ---------------- Methods / provenance ----------------
    elements.append(_p("Methods & Provenance", header))
    methods_html = (
        f"<b>Genome build:</b> {genome_build}<br/>"
        f"<b>Annotation source:</b> {annotation_source}"
        + (f" (version/date: {annotation_source_version})" if annotation_source_version else " (version not recorded — add to audit log)")
        + f"<br/><b>Classification engine:</b> {acmg_engine_version}<br/>"
        "<b>Note on evidence scope:</b> a subset of ACMG-AMP 2015 criteria "
        "require data (segregation, functional studies, case-cohort data) "
        "not available from variant-level annotation alone; these are "
        "explicitly recorded as not assessed rather than assumed absent."
    )
    elements.append(_p(methods_html, small))
    elements.append(Spacer(1, 10))

    # ---------------- Disclaimers ----------------
    elements.append(_p("Disclaimers", subheader))
    disclaimer_html = (
        "This report reflects analysis based on the clinical and sample "
        "information supplied; accuracy depends on the correctness of that "
        "information. Classification reflects current knowledge and may "
        "change as evidence evolves. This document may not be copied or "
        "reproduced except in totality."
    )
    elements.append(_p(disclaimer_html, small))
    elements.append(Spacer(1, 14))

    # ---------------- Signature ----------------
    if signatory_name:
        elements.append(_p(f"Reviewed by: {signatory_name}"
                            + (f", {signatory_role}" if signatory_role else ""), normal))
    else:
        elements.append(_p("[Reviewing signatory not yet recorded]", small))
    elements.append(Spacer(1, 10))

    # ---------------- Technical appendix (plain text, no raw JSON) ----------------
    if include_technical_appendix and "Evidence" in df.columns:
        elements.append(_p("Technical Appendix — Evidence Detail", header))
        for _, r in reportable.iterrows():
            import json
            try:
                ev = json.loads(r.get("Evidence", "{}"))
            except Exception:
                ev = {}
            gene = r.get("GENE", "")
            score = ev.get("acmg_score", "n/a")
            criteria_str = ev.get("acmg_criteria", "")
            criteria_list = [c.strip() for c in criteria_str.split(",") if c.strip()]
            lines = [f"<b>{gene}</b> — GeneBe ACMG score: {score}"]
            for code in criteria_list:
                lines.append(f"&nbsp;&nbsp;{code}")
            elements.append(_p("<br/>".join(lines), small))
            elements.append(Spacer(1, 6))

    def _footer(canvas, doc_):
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(doc_.leftMargin, 0.7 * cm,
                           f"Patient ID: {patient_id or 'N/A'}")
        canvas.drawRightString(A4[0] - doc_.rightMargin, 0.7 * cm,
                                f"Page {canvas.getPageNumber()}")

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
