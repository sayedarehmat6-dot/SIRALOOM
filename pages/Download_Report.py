import io
import streamlit as st
from annotations.report_v2 import generate_clinical_report

st.set_page_config(page_title="Download Report — Siraloom", page_icon="")
st.title("Download Report")

if "last_result_df" not in st.session_state:
    st.warning("Run the Annotation Service or Reanalysis Service first — this page "
               "generates a report from that result.")
    st.stop()

result_df = st.session_state["last_result_df"]
source_service = st.session_state.get("last_service", "")
st.caption(f"Generating report from: {source_service} result ({len(result_df)} variant(s)).")

st.markdown("### Laboratory & Report Details")
st.caption("Enter your laboratory's information below — it will appear on the generated report.")

with st.form("report_details"):
    col1, col2 = st.columns(2)
    with col1:
        lab_name = st.text_input("Laboratory name", "")
        lab_contact = st.text_input("Laboratory contact (email / phone)", "")
        referring_physician = st.text_input("Referring physician (optional)", "")
        signatory_name = st.text_input("Reviewing signatory (optional)", "")
        signatory_role = st.text_input("Signatory role/title (optional)", "")
    with col2:
        patient_id = st.text_input("Patient ID", "")
        patient_dob = st.text_input("Patient DOB (optional)", "")
        patient_sex = st.text_input("Patient sex (optional)", "")
        sample_id = st.text_input("Sample ID", "")
        clinical_indication = st.text_input("Clinical indication (optional)", "")

    logo_file = st.file_uploader("Laboratory logo (optional, not yet rendered in v1 template)", type=["png", "jpg", "jpeg"])

    submitted = st.form_submit_button("Generate PDF Report")

if not submitted:
    st.stop()

if not lab_name or not lab_contact:
    st.error("Laboratory name and contact are required.")
    st.stop()

pdf_buffer = io.BytesIO()
try:
    generate_clinical_report(
        result_df,
        buffer=pdf_buffer,
        lab_name=lab_name,
        lab_contact=lab_contact,
        referring_physician=referring_physician or None,
        signatory_name=signatory_name or None,
        signatory_role=signatory_role or None,
        patient_id=patient_id or None,
        patient_dob=patient_dob or None,
        patient_sex=patient_sex or None,
        sample_id=sample_id or None,
        clinical_indication=clinical_indication or None,
        annotation_source="GeneBe API (ACMG-AMP 2015 implementation)",
        annotation_source_version=f"queried {__import__('pandas').Timestamp.now(tz='UTC').strftime('%Y-%m-%d')}",
        acmg_engine_version="GeneBe ACMG-AMP 2015 (Stawiński & Płoski)",
    )
    st.success("Report generated.")
    st.download_button(
        "Download PDF Report",
        data=pdf_buffer.getvalue(),
        file_name=f"{sample_id or 'report'}_siraloom_report.pdf",
        mime="application/pdf",
    )
except Exception as e:
    st.error(f"Report generation failed: {e}")
