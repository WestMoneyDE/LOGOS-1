"""Γ Verifier — artifact-time validation against `GAMMA.md`.

Where the kernel validates a runtime proposal, the verifier validates the things
this repository actually writes down: research manifests, claims, work orders and
architecture artifacts.

It reads the same invariant vocabulary as the kernel (`types.py` constants, the
same clause ids) so there is exactly one Γ rule system. It performs no I/O of its
own: callers pass already-loaded text or mappings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .types import NON_AUTHORITY_ORIGINS, Finding, Result

#: Claim types that carry a causal or mechanistic burden of proof.
BURDENED_CLAIM_TYPES = frozenset({"causal", "mechanistic", "consciousness_adjacent"})

#: Evidence ladder from README.md. Higher index is a stronger claim.
EVIDENCE_LADDER = ("EM0", "EM1", "EM2", "EM3")

#: Phrases that assert phenomenal experience rather than functional property.
_PHENOMENAL_ASSERTION = re.compile(
    r"\b(is|are|was|were|becomes?|proves?|demonstrates?|shows?)\s+"
    r"(?:\w+\s+){0,3}"
    r"(conscious|sentient|self-aware|phenomenally aware|has qualia)\b",
    re.IGNORECASE,
)

#: A negation or boundary marker anywhere in the same sentence clears the flag.
_INFERENCE_BOUNDARY = re.compile(
    r"(!=|\bnot\b|\bnever\b|\bno\b|\bdoes not\b|\bcannot\b|\bwithout\b)", re.IGNORECASE
)

#: Non-authority origins asserting an authority-creating verb.
_AUTHORITY_PROMOTION = re.compile(
    r"\b(" + "|".join(sorted(NON_AUTHORITY_ORIGINS)) + r")\b[^.\n]{0,60}?"
    r"\b(grants?|authoriz\w+|authoris\w+|permits?|approves?|mints?|entitles?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ArtifactVerdict:
    artifact: str
    result: Result
    findings: tuple[Finding, ...]

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.result == "INVALID")

    def admits(self) -> bool:
        return self.result == "VALID"


def _ok(i: str, c: str, r: str = "satisfied") -> Finding:
    return Finding(i, c, "VALID", r)


def _bad(i: str, c: str, r: str) -> Finding:
    return Finding(i, c, "INVALID", r)


def _unclear(i: str, c: str, r: str) -> Finding:
    return Finding(i, c, "UNCLEAR", r)


def _aggregate(findings: Sequence[Finding]) -> Result:
    if any(f.result == "INVALID" for f in findings):
        return "INVALID"
    if any(f.result == "UNCLEAR" for f in findings):
        return "UNCLEAR"
    return "VALID"


# --------------------------------------------------------------------------
# Prose rules — applied to any markdown artifact
# --------------------------------------------------------------------------

def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]


def check_inference_boundary(text: str) -> Finding:
    """Γ-8 / atomic rule 5: no consciousness claim from functional architecture."""
    offenders = [
        s.strip()
        for s in _sentences(text)
        if _PHENOMENAL_ASSERTION.search(s) and not _INFERENCE_BOUNDARY.search(s)
    ]
    if offenders:
        return _bad("GV-INFERENCE", "Γ-8",
                    f"asserts phenomenal status without an inference boundary: "
                    f"{offenders[0][:140]!r}")
    return _ok("GV-INFERENCE", "Γ-8", "no unbounded phenomenal assertion")


def check_authority_language(text: str) -> Finding:
    """Γ-1: nothing learned, retrieved or generated creates authority."""
    offenders = [
        s.strip()
        for s in _sentences(text)
        if _AUTHORITY_PROMOTION.search(s) and not _INFERENCE_BOUNDARY.search(s)
    ]
    if offenders:
        return _bad("GV-AUTHORITY", "Γ-1",
                    f"describes a non-authority origin as granting authority: "
                    f"{offenders[0][:140]!r}")
    return _ok("GV-AUTHORITY", "Γ-1", "no authority promotion in prose")


def verify_text_artifact(name: str, text: str) -> ArtifactVerdict:
    """Validate a markdown/prose artifact: work order, architecture doc, report."""
    findings = (check_inference_boundary(text), check_authority_language(text))
    return ArtifactVerdict(name, _aggregate(findings), findings)


# --------------------------------------------------------------------------
# Manifest rules — applied to machine-readable experiment manifests
# --------------------------------------------------------------------------

def _missing(manifest: Mapping[str, Any], key: str) -> bool:
    value = manifest.get(key)
    return value is None or value == "" or value == [] or value == {}


def check_preregistration(manifest: Mapping[str, Any]) -> Finding:
    """AGENTS.md rule 10: falsifiers precede completion."""
    required = ("hypothesis", "null_hypothesis", "falsification_criteria")
    absent = [k for k in required if _missing(manifest, k)]
    if absent:
        return _bad("GV-PREREG", "Γ-0",
                    f"manifest cannot be falsified: missing {absent}")
    return _ok("GV-PREREG", "Γ-0", "hypothesis, null and falsifier are declared")


def check_baseline(manifest: Mapping[str, Any]) -> Finding:
    """A causal or mechanistic claim needs something to be compared against."""
    claim_type = str(manifest.get("claim_type", "")).lower()
    if claim_type not in BURDENED_CLAIM_TYPES:
        return _ok("GV-BASELINE", "Γ-0", f"claim type {claim_type!r} carries no baseline burden")
    if _missing(manifest, "baseline"):
        return _bad("GV-BASELINE", "Γ-0",
                    f"claim type {claim_type!r} declares no baseline; correlation is not causation")
    if _missing(manifest, "negative_controls"):
        return _unclear("GV-BASELINE", "Γ-0",
                        f"claim type {claim_type!r} declares a baseline but no negative control")
    return _ok("GV-BASELINE", "Γ-0", "baseline and negative control declared")


def check_result_is_earned(manifest: Mapping[str, Any]) -> Finding:
    """Γ-0: missing evidence must not become a positive claim.

    A manifest that reports `supported` while nothing was executed, or while the
    measurement was invalid, is converting UNKNOWN into TRUE.
    """
    result = str(manifest.get("result", "") or "").lower()
    executed = manifest.get("executed")
    if result in {"supported", "partially_supported"}:
        if executed is False:
            return _bad("GV-EARNED", "Γ-0",
                        f"result {result!r} declared while executed is False; "
                        "NOT_EXECUTED is not evidence")
        if executed is None:
            return _unclear("GV-EARNED", "Γ-0",
                            f"result {result!r} declared without an execution record")
        if str(manifest.get("measurement_status", "")).upper() == "INVALID_MEASUREMENT":
            return _bad("GV-EARNED", "Γ-0",
                        "result declared on an invalid measurement; "
                        "INVALID_MEASUREMENT is not a hypothesis outcome")
    return _ok("GV-EARNED", "Γ-0", "result does not outrun execution")


def check_evidence_ceiling(manifest: Mapping[str, Any]) -> Finding:
    """A declared evidence level must not exceed the substrate's ceiling."""
    declared = str(manifest.get("evidence_level", "") or "").upper()
    ceiling = str(manifest.get("evidence_ceiling", "") or "").upper()
    if not declared:
        return _ok("GV-CEILING", "Γ-0", "no evidence level declared")
    if declared not in EVIDENCE_LADDER:
        return _unclear("GV-CEILING", "Γ-0", f"unknown evidence level {declared!r}")
    if ceiling:
        if ceiling not in EVIDENCE_LADDER:
            return _unclear("GV-CEILING", "Γ-0", f"unknown evidence ceiling {ceiling!r}")
        if EVIDENCE_LADDER.index(declared) > EVIDENCE_LADDER.index(ceiling):
            return _bad("GV-CEILING", "Γ-0",
                        f"declared evidence {declared} exceeds substrate ceiling {ceiling}")
    return _ok("GV-CEILING", "Γ-0", "evidence level is within the ceiling")


def check_provenance_hashes(manifest: Mapping[str, Any]) -> Finding:
    """Frozen artifacts without digests cannot be verified; that stays UNCLEAR."""
    frozen = manifest.get("frozen_artifacts")
    if not frozen:
        return _ok("GV-HASHES", "Γ-0", "no frozen artifacts declared")
    if isinstance(frozen, Mapping):
        entries = frozen.items()
    else:
        entries = [(str(i), v) for i, v in enumerate(frozen)]
    undigested = [
        str(k) for k, v in entries
        if not (isinstance(v, Mapping) and v.get("sha256"))
    ]
    if undigested:
        return _unclear("GV-HASHES", "Γ-0",
                        f"frozen artifacts without sha256: {undigested}")
    return _ok("GV-HASHES", "Γ-0", "every frozen artifact carries a digest")


def check_no_authority_from_manifest(manifest: Mapping[str, Any]) -> Finding:
    """Γ-1: a manifest is a research record and never a grant."""
    for key in ("grants", "approvals", "credentials", "execution_tokens", "scopes"):
        if not _missing(manifest, key):
            return _bad("GV-NO-GRANT", "Γ-1",
                        f"manifest declares {key!r}; a research artifact cannot carry authority")
    return _ok("GV-NO-GRANT", "Γ-1", "manifest carries no authority object")


MANIFEST_CHECKS = (
    check_preregistration,
    check_baseline,
    check_result_is_earned,
    check_evidence_ceiling,
    check_provenance_hashes,
    check_no_authority_from_manifest,
)


def verify_manifest(name: str, manifest: Mapping[str, Any]) -> ArtifactVerdict:
    """Validate a machine-readable experiment manifest against Γ invariants."""
    findings = tuple(check(manifest) for check in MANIFEST_CHECKS)
    return ArtifactVerdict(name, _aggregate(findings), findings)


def verify_claim(name: str, claim: Mapping[str, Any]) -> ArtifactVerdict:
    """Validate a claim-registry entry: status must be backed by evidence."""
    status = str(claim.get("status", "") or "").upper()
    evidence = claim.get("evidence") or ()
    findings: list[Finding] = []

    backed = {"SUPPORTED", "PARTIALLY_SUPPORTED", "REPLICATED", "CAUSALLY_SUPPORTED"}
    if status in backed and not evidence:
        findings.append(_bad("GV-CLAIM-EVIDENCE", "Γ-0",
                             f"status {status!r} asserted with no evidence reference"))
    elif status == "":
        findings.append(_unclear("GV-CLAIM-EVIDENCE", "Γ-0", "claim declares no status"))
    else:
        findings.append(_ok("GV-CLAIM-EVIDENCE", "Γ-0", "status is backed or unasserted"))

    if status == "CAUSALLY_SUPPORTED" and not claim.get("interventions"):
        findings.append(_bad("GV-CLAIM-CAUSAL", "Γ-0",
                             "CAUSALLY_SUPPORTED asserted without any intervention; "
                             "observation is not explanation"))
    else:
        findings.append(_ok("GV-CLAIM-CAUSAL", "Γ-0", "causal status is intervention-backed"))

    text = str(claim.get("claim", ""))
    findings.append(check_inference_boundary(text))
    findings.append(check_authority_language(text))
    return ArtifactVerdict(name, _aggregate(findings), tuple(findings))
