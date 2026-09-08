import streamlit as st
import pandas as pd
from utils.pipeline_engine import load_raw_vcf, annotate_and_classify

st.set_page_config(page_title="Annotation Service — Siraloom", page_icon="🧪")
st.title("🧪 Annotation Service")
st.caption(
    "Upload a VCF for variant annotation and ACMG-AMP 2015 classification. "
    "This demonstration uses a public annotation API for fast evaluation — "
    "a production deployment runs on your own hosted infrastructure."
)

uploaded_vcf = st.file_uploader("Upload a VCF file", type=["vcf"])

if uploaded_vcf is None:
    st.info("Upload a VCF to begin.")
    st.stop()

with st.spinner("Annotating and classifying..."):
    try:
        variants_df, build_info = load_raw_vcf(uploaded_vcf)
        result_df = annotate_and_classify(variants_df)
    except Exception as e:
        st.error(f"Something went wrong processing this file: {e}")
        st.stop()

if build_info.get("warning"):
    st.warning(f"⚠️ {build_info['warning']}")

# --- filter to clinically relevant results only (benign excluded from main view) ---
reportable_df = result_df[
    ~result_df["ACMG"].astype(str).str.contains("benign", case=False, na=False)
]

st.success(f"Processed {len(result_df)} variant(s) — {len(reportable_df)} clinically relevant.")

if reportable_df.empty:
    st.write("No clinically significant candidate variants identified.")
else:
    display_df = reportable_df[["GENE", "HGVSc", "HGVSp", "CONSEQUENCE", "ACMG", "ClinVar"]].rename(
        columns={"GENE": "Gene", "CONSEQUENCE": "Consequence", "ACMG": "Classification", "ClinVar": "ClinVar"}
    )
    st.dataframe(display_df, use_container_width=True)

st.session_state["last_result_df"] = result_df
st.session_state["last_service"] = "Annotation Service"

st.markdown("---")
st.info("To generate a formatted PDF report with your laboratory's details, open **Download Report** in the sidebar.")
