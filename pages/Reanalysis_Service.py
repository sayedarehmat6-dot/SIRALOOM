import streamlit as st
import json
from utils.pipeline_engine import load_raw_vcf, annotate_and_classify

st.set_page_config(page_title="Reanalysis Service — Siraloom", page_icon="")
st.title("Reanalysis Service")
st.caption(
    "Upload a previously unsolved case for reanalysis against current "
    "reference evidence. This demonstration uses a public annotation API "
    "for fast evaluation — a production deployment runs on your own "
    "hosted infrastructure, and no patient-identifying information is "
    "required for either."
)

col1, col2 = st.columns(2)
with col1:
    uploaded_vcf = st.file_uploader("Upload case VCF", type=["vcf"])
with col2:
    prior_findings_file = st.file_uploader(
        "Optional: prior report findings (JSON list of gene names already reported)",
        type=["json"],
    )

if uploaded_vcf is None:
    st.info("Upload a case VCF to begin.")
    st.stop()

prior_genes = set()
if prior_findings_file is not None:
    try:
        prior_genes = set(json.load(prior_findings_file))
    except Exception:
        st.warning("Could not read prior findings file — proceeding without it.")

with st.spinner("Reanalyzing against current reference evidence..."):
    try:
        variants_df = load_raw_vcf(uploaded_vcf)
        result_df = annotate_and_classify(variants_df)
    except Exception as e:
        st.error(f"Something went wrong processing this file: {e}")
        st.stop()

reportable_df = result_df[
    ~result_df["ACMG"].astype(str).str.contains("benign", case=False, na=False)
]
new_findings_df = reportable_df[~reportable_df["GENE"].isin(prior_genes)]

st.success(f"Reanalysis complete — {len(reportable_df)} clinically relevant candidate(s).")

if not new_findings_df.empty:
    st.markdown("### New candidate finding(s) not in prior report")
    st.dataframe(
        new_findings_df[["GENE", "HGVSc", "HGVSp", "ACMG", "ClinVar"]],
        use_container_width=True,
    )
elif not reportable_df.empty:
    st.write("Candidate finding(s) identified — all previously reported.")
    st.dataframe(reportable_df[["GENE", "HGVSc", "HGVSp", "ACMG", "ClinVar"]], use_container_width=True)
else:
    st.write("No clinically significant candidate identified on this reanalysis pass.")

st.session_state["last_result_df"] = result_df
st.session_state["last_service"] = "Reanalysis Service"

st.markdown("---")
st.info("To generate a formatted PDF report with your laboratory's details, open **Download Report** in the sidebar.")
