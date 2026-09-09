"""
utils/pipeline_engine.py
=========================
Shared core used by both the Annotation Service and Reanalysis Service
pages, so the two "services" are genuinely one engine with two front
doors — not duplicated logic that can drift apart.

API key setup (do this before deploying):
  1. In your Streamlit Cloud app settings -> Secrets, add:
       [genebe]
       username = "your_account_email"
       api_key = "your_api_key"
  2. Locally, create .streamlit/secrets.toml with the same content
     (and make sure .streamlit/secrets.toml is in .gitignore — never
     commit real credentials).
"""

import streamlit as st

try:
    import genebe as gnb
except ImportError:
    gnb = None


def get_genebe_credentials():
    """Returns (username, api_key) from st.secrets, or (None, None) for
    anonymous/rate-limited use if secrets aren't configured yet."""
    try:
        creds = st.secrets["genebe"]
        return creds.get("username"), creds.get("api_key")
    except Exception:
        return None, None


def load_raw_vcf(file_obj, apply_normalization: bool = False):
    import io
    import gzip
    import pandas as pd
    from utils.validate_normalize import detect_reference_build, trim_parsimonious

    rows = []
    header_lines = []

    raw_bytes = file_obj.read()
    if raw_bytes[:2] == b"\x1f\x8b":  # gzip magic bytes — handles .vcf.gz uploads
        raw_bytes = gzip.decompress(raw_bytes)
    text = io.TextIOWrapper(io.BytesIO(raw_bytes), encoding="utf-8")

    for line in text:
        if line.startswith("##"):
            header_lines.append(line.strip())
            continue
        if line.startswith("#CHROM"):
            continue
        parts = line.strip().split("\t")
        if len(parts) < 5:
            continue
        chrom, pos, _id, ref, alt_field = parts[:5]
        for alt in alt_field.split(","):
            if apply_normalization:
                norm_pos, norm_ref, norm_alt = trim_parsimonious(int(pos), ref, alt)
            else:
                norm_pos, norm_ref, norm_alt = int(pos), ref, alt
            rows.append({
                "CHROM": chrom.replace("chr", ""),
                "POS": norm_pos,
                "REF": norm_ref,
                "ALT": norm_alt,
            })
    build_info = detect_reference_build(header_lines)
    return pd.DataFrame(rows), build_info


def annotate_and_classify(variants_df):
    """
    Calls GeneBe (authenticated if secrets are configured, anonymous
    otherwise) and returns an annotated DataFrame with GENE, CONSEQUENCE,
    ClinVar, ClinVar_review, gnomAD_AF, HGVSc, HGVSp, ACMG, ACMG_Score,
    Rules, Evidence columns — using GeneBe's own validated ACMG-AMP 2015
    engine, not a custom classifier.

    Raises RuntimeError with a clear message on failure; the caller
    decides how to present that to the user.
    """
    if gnb is None:
        raise RuntimeError("`genebe` package not installed — add `genebe` to requirements.txt.")
    if variants_df.empty:
        raise RuntimeError("No variants to annotate.")

    variant_strings = [f"{r.CHROM}-{r.POS}-{r.REF}-{r.ALT}" for r in variants_df.itertuples()]
    username, api_key = get_genebe_credentials()

    kwargs = {"genome": "hg38", "output_format": "list"}
    if username and api_key:
        kwargs["username"] = username
        kwargs["api_key"] = api_key

    raw_result = gnb.annotate(variant_strings, **kwargs)

    if isinstance(raw_result, dict) and "variants" in raw_result:
        variants = raw_result["variants"]
    elif isinstance(raw_result, list) and raw_result and isinstance(raw_result[0], dict):
        variants = raw_result
    else:
        raise RuntimeError(
            "GeneBe returned an unexpected response shape. If you recently "
            "changed accounts or the genebe package version, verify the "
            "response format against docs.genebe.net before trusting output."
        )

    def _g(v, key, default=""):
        return v.get(key, default) if isinstance(v, dict) else default

    def _first_hgvs(v, field):
        cons = v.get("consequences") if isinstance(v, dict) else None
        if cons and isinstance(cons[0], dict):
            return cons[0].get(field, "")
        return ""

    df = variants_df.copy()
    df["GENE"] = [_g(v, "gene_symbol") for v in variants]
    df["CONSEQUENCE"] = [_g(v, "effect") for v in variants]
    df["ClinVar"] = [_g(v, "clinvar_classification") for v in variants]
    df["ClinVar_review"] = [_g(v, "clinvar_review_status") for v in variants]
    df["gnomAD_AF"] = [_g(v, "frequency_reference_population") for v in variants]
    df["HGVSc"] = [_first_hgvs(v, "hgvs_c") for v in variants]
    df["HGVSp"] = [_first_hgvs(v, "hgvs_p") for v in variants]
    df["ACMG"] = [_g(v, "acmg_classification") for v in variants]
    df["Rules"] = [_g(v, "acmg_criteria") for v in variants]
    df["ACMG_Score"] = [_g(v, "acmg_score") for v in variants]
    df["Evidence"] = [
        f'{{"classification_source": "genebe_acmg_2015", '
        f'"acmg_score": {v.get("acmg_score") if isinstance(v, dict) else "null"}, '
        f'"acmg_criteria": "{v.get("acmg_criteria", "") if isinstance(v, dict) else ""}"}}'
        for v in variants
    ]
    return df
