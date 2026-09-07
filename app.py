import streamlit as st

st.set_page_config(page_title="Siraloom", page_icon="", layout="wide")

st.title("Siraloom")
st.subheader("Variant annotation and reanalysis for clinical genetics laboratories")

st.markdown(
    """
Siraloom helps clinical genetics laboratories get more out of the sequencing
they've already run — through fast, ACMG-AMP 2015-aligned variant annotation,
and continuous reanalysis of previously unsolved cases.
"""
)

st.markdown("---")
st.header("Our Services")

col1, col2 = st.columns(2)

with col1:
    st.markdown("###  Annotation Service")
    st.markdown(
        """
Upload a VCF and receive filtered, clinically relevant variant annotation —
population frequency, ClinVar precedent, and ACMG-AMP 2015 classification —
in a structured report.

*Use the sidebar to open the Annotation Service page.*
"""
    )

with col2:
    st.markdown("###  Reanalysis Service")
    st.markdown(
        """
Run continuous reanalysis against your unsolved case backlog. As reference
databases update, previously unresolved cases are re-evaluated and flagged
for physician review when new evidence emerges.

*Use the sidebar to open the Reanalysis Service page.*
"""
    )

st.markdown("---")
st.header("How this works")
st.markdown(
    """
**This demonstration** runs on a public annotation API for fast, no-setup
evaluation — no patient-identifying information is required to try it.

**A production deployment** runs entirely on your own infrastructure: your
laboratory hosts the reference databases, and the pipeline runs against
your local data. No case data leaves your servers.
"""
)

st.markdown("---")
st.header("Contact")
st.markdown(
    """
**[SAYEDA REHMAT]** — Bioinformatician
 [sayedarehmat6@gmail.com]
"""
)

st.caption(
    "Automated classification is intended as decision support for review by "
    "qualified laboratory personnel — not a diagnostic report of record."
)
