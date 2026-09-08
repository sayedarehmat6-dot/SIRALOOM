"""
utils/validate_normalize.py
=============================
Two distinct, honestly-scoped things, often confused as one:

1. REFERENCE BUILD VALIDATION — checking the uploaded VCF actually claims
   the genome build we assume (GRCh38/hg38). GeneBe's API assumes hg38 and
   auto-lifts over hg19 coordinates for its convenience VCF-file client —
   but we are calling the raw list-based `annotate()` endpoint directly
   (see pipeline_engine.py), not that convenience client, so we should NOT
   assume liftover is happening automatically. If a lab uploads a GRCh37
   VCF and we silently treat it as GRCh38, coordinates will be wrong and
   nothing will error — it'll just silently return incorrect annotations
   for indels/SNVs alike. This module checks header metadata and flags
   ambiguity rather than assuming.

2. VARIANT NORMALIZATION — representing each variant consistently
   (parsimonious: as few bases as possible; left-aligned: shifted as far
   left as the reference sequence allows). This module implements
   PARSIMONY TRIMMING ONLY (removing redundant shared bases between REF
   and ALT) — this needs no reference FASTA and fixes many real-world
   representation inconsistencies.

   HONEST LIMITATION: true left-alignment across repetitive/homopolymer
   regions requires knowing the actual reference sequence, which requires
   either a local reference FASTA (the exact GB-scale download problem
   this project has deliberately avoided) or an external normalization
   service. GeneBe's docs reference a "convert" API endpoint for exactly
   this — worth checking docs.genebe.net for its precise usage before
   assuming it's wired in here; it is NOT yet implemented in this file.
   Until one of those is added, variants in repetitive regions may still
   reach GeneBe in a technically-valid but non-canonical representation,
   which can cause false "not found" ClinVar/gnomAD lookups — exactly the
   class of bug that caused the earlier BRCA1 coordinate mismatch, just a
   different specific cause (that was a wrong genomic position; this is
   about ties given a *correct* position but non-canonical REF/ALT length).
"""

from typing import List, Optional, Tuple, Dict

# Known chr1 lengths — a simple, no-download way to fingerprint genome build
# from VCF header ##contig lines, if present.
CHR1_LENGTH_BY_BUILD = {
    248956422: "GRCh38",
    249250621: "GRCh37",
}


def detect_reference_build(header_lines: List[str]) -> Dict[str, Optional[str]]:
    """
    Inspects VCF header lines for explicit ##reference= or ##contig
    length hints. Returns {"declared": ..., "detected_from_contig": ...,
    "warning": ...}. Does not guess silently — if nothing is found, says so.
    """
    declared = None
    detected = None
    for line in header_lines:
        if line.startswith("##reference"):
            declared = line.split("=", 1)[-1].strip()
        if line.startswith("##contig=<ID=1,") or line.startswith("##contig=<ID=chr1,"):
            for part in line.split(","):
                if part.startswith("length="):
                    try:
                        length = int(part.split("=")[1].rstrip(">"))
                        detected = CHR1_LENGTH_BY_BUILD.get(length)
                    except ValueError:
                        pass

    warning = None
    if declared is None and detected is None:
        warning = ("No ##reference or recognizable ##contig length found in "
                    "VCF header — genome build is ASSUMED to be GRCh38/hg38, "
                    "not confirmed. Verify manually before trusting results.")
    elif detected and "38" not in (declared or "") and detected != "GRCh38":
        warning = (f"Contig length suggests {detected}, not GRCh38. This "
                    f"pipeline assumes GRCh38 — results will be silently "
                    f"wrong if this VCF is actually {detected}.")

    return {"declared": declared, "detected_from_contig": detected, "warning": warning}


def trim_parsimonious(pos: int, ref: str, alt: str) -> Tuple[int, str, str]:
    """
    Removes redundant shared bases between REF and ALT (parsimony only —
    NOT full left-alignment, which needs the reference sequence). Adjusts
    POS accordingly. Never reduces either allele to zero length.

    Example: POS=100 REF=CTCT ALT=CTCTCT (a duplication) has no shared
    trailing/leading trim opportunity here since alt is longer at the end;
    a case like REF=ATG ALT=ATGTG *does* trim to REF=A ALT=ATG at the same
    effective right-anchor — trimming shared PREFIX only when a shared
    SUFFIX remains, matching standard parsimony rules.
    """
    ref, alt = str(ref), str(alt)

    # Trim shared suffix (from the right), keeping at least 1 base each
    while len(ref) > 1 and len(alt) > 1 and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]

    # Trim shared prefix (from the left), adjusting position, keeping >=1 base each
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref, alt = ref[1:], alt[1:]
        pos += 1

    return pos, ref, alt
