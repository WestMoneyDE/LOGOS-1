"""Infrastructure adapter tests that need no running service.

These cover the acceptance conditions of Queue 1 that are testable against the
in-repo adapters. They do **not** demonstrate materialization: no PostgreSQL,
MLflow, Langfuse, MinIO, OTel collector or DVC remote is exercised here.

```text
Mocked != Materialized
```

The service-backed acceptance tests are blocked; see
`docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`.
"""
from __future__ import annotations

import hashlib
import json
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_research.infra import (
    DatasetRevision,
    ExperimentIdentity,
    ExternalRefs,
    InMemoryDatasetLineageStore,
    InMemoryResearchRepository,
    InfrastructureUnavailable,
    LocalArtifactStore,
    NoOpLLMTraceSink,
    NoOpRunTracker,
    NoOpTraceSink,
    ResearchRun,
    ResearchStack,
    RunRecord,
    UnavailableRepository,
    correlation_tags,
    environment_id,
    redact,
    resolve_from_experiment_id,
)

EXPERIMENT = "INFRA-MATERIALIZATION-SMOKE-R1"


def identity(**overrides) -> ExperimentIdentity:
    base = dict(experiment_id=EXPERIMENT, experiment_revision=1,
                preregistration_hash="a" * 64, git_sha="96a3c10",
                gamma_version="v0.2")
    base.update(overrides)
    return ExperimentIdentity(**base)


def stack(**overrides) -> ResearchStack:
    base = dict(repository=InMemoryResearchRepository(), artifacts=LocalArtifactStore(),
                lineage=InMemoryDatasetLineageStore(), tracker=NoOpRunTracker(),
                traces=NoOpTraceSink(), llm_traces=NoOpLLMTraceSink())
    base.update(overrides)
    return ResearchStack(**base)


# --------------------------------------------------------------------------
# Canonical identity dominates external identifiers
# --------------------------------------------------------------------------

def test_one_canonical_identity_resolves_every_external_reference():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    run.trace("gamma_validation", {"result": "VALID"})
    run.llm_generation({"model": "fake", "prompt": "hi"})
    run.put_artifact("out.json", b'{"ok":true}')
    run.record_dataset(DatasetRevision("fixture", "rev1", "obj", "sem"))
    run.finish()

    view = resolve_from_experiment_id(s, EXPERIMENT)
    entry = view["runs"][0]
    for key in ("mlflow_run_id", "langfuse_trace_id", "otel_trace_id"):
        assert entry[key], f"{key} not correlated"
    assert entry["dvc_dataset_revs"] and entry["artifact_ids"]
    assert entry["preregistration_hash"] == "a" * 64


def test_external_identifiers_never_replace_canonical_identity():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    record = run.start()
    assert record.run_id == "run-1"
    assert record.external.mlflow_run_id != record.run_id


def test_correlation_tags_carry_logos_identity_and_no_secret():
    tags = correlation_tags(identity(), "run-1")
    assert tags["logos.experiment_id"] == EXPERIMENT
    assert tags["logos.run_id"] == "run-1"
    assert tags["logos.preregistration_hash"] == "a" * 64
    joined = json.dumps(tags).lower()
    for marker in ("secret", "password", "token", "api_key"):
        assert marker not in joined


def test_environment_id_refuses_secret_inputs():
    with pytest.raises(ValueError):
        environment_id({"python": "3.12", "S3_SECRET_ACCESS_KEY": "x"})
    assert environment_id({"python": "3.12"}) == environment_id({"python": "3.12"})


# --------------------------------------------------------------------------
# Operational status is not a scientific verdict
# --------------------------------------------------------------------------

def test_completed_run_may_carry_a_falsified_verdict():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    record = run.finish(scientific_verdict="FALSIFIED")
    assert record.status == "COMPLETED"
    assert record.scientific_verdict == "FALSIFIED"
    assert record.problems() == ()


def test_a_failed_run_may_carry_no_verdict_at_all():
    record = RunRecord(run_id="r", identity=identity(), status="FAILED")
    assert record.scientific_verdict is None
    assert record.problems() == ()


def test_a_verdict_on_a_running_run_is_flagged():
    record = RunRecord(run_id="r", identity=identity(), status="RUNNING",
                       scientific_verdict="SUPPORTED")
    assert any("requires a completed" in p for p in record.problems())


# --------------------------------------------------------------------------
# Fail-closed canonical, fail-degraded observability
# --------------------------------------------------------------------------

def test_canonical_persistence_failure_aborts_rather_than_falling_back():
    """The forbidden workflow: Postgres down, write local JSON, report success."""
    s = stack(repository=UnavailableRepository())
    run = ResearchRun(s, identity(), "run-1")
    with pytest.raises(InfrastructureUnavailable):
        run.start()
    assert s.canonical_unusable() == ("unavailable-repository",)


def test_observability_failure_degrades_and_is_recorded():
    s = stack(traces=NoOpTraceSink(available=False))
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    run.trace("gamma_validation")
    record = run.finish()
    assert record.status == "DEGRADED"
    assert [d.sink for d in record.degraded_sinks] == ["trace_sink"]
    assert record.degraded_sinks[0].lost_capability == "system traces"


def test_missing_telemetry_is_distinguishable_from_nothing_happening():
    """The whole point of DegradedSink."""
    quiet = stack()
    quiet_run = ResearchRun(quiet, identity(), "run-quiet")
    quiet_run.start()
    quiet_record = quiet_run.finish()

    broken = stack(llm_traces=NoOpLLMTraceSink(available=False))
    broken_run = ResearchRun(broken, identity(), "run-broken")
    broken_run.start()
    broken_run.llm_generation({"model": "fake"})
    broken_record = broken_run.finish()

    assert quiet_record.external.langfuse_trace_id is None
    assert broken_record.external.langfuse_trace_id is None
    assert quiet_record.degraded_sinks == ()
    assert broken_record.degraded_sinks != ()
    assert quiet_record.status == "COMPLETED"
    assert broken_record.status == "DEGRADED"


def test_in_memory_repository_never_claims_to_be_persistent():
    """A caller must be able to tell durable storage from a dict."""
    health = InMemoryResearchRepository().health()
    assert health.status == "CONFIGURED"
    assert health.status != "PERSISTENT"
    assert "not durable" in health.detail


# --------------------------------------------------------------------------
# Artifacts: content integrity and idempotency
# --------------------------------------------------------------------------

def test_artifact_roundtrip_preserves_exact_bytes():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    payload = b'{"a":1}\r\n{"a":2}\r\n'
    ref = run.put_artifact("d.jsonl", payload)
    assert s.artifacts.get(ref.artifact_id) == payload
    assert ref.content_sha256 == hashlib.sha256(payload).hexdigest()
    assert s.artifacts.verify(ref)


def test_identical_content_is_one_artifact_identity():
    """A retried upload must not mint a second artifact."""
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    first = run.put_artifact("a.bin", b"same")
    second = run.put_artifact("b.bin", b"same")
    assert first.artifact_id == second.artifact_id


def test_exact_byte_identity_and_semantic_row_identity_are_separate():
    """The R4 CRLF/LF lesson, carried into the infrastructure design."""
    crlf = b'{"a":1}\r\n{"a":2}\r\n'
    lf = crlf.replace(b"\r\n", b"\n")

    def rows(blob: bytes) -> str:
        parsed = [json.loads(line) for line in blob.decode().splitlines() if line.strip()]
        return hashlib.sha256(
            json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    revision_crlf = DatasetRevision("fixture", "rev-crlf",
                                    hashlib.sha256(crlf).hexdigest(), rows(crlf))
    revision_lf = DatasetRevision("fixture", "rev-lf",
                                  hashlib.sha256(lf).hexdigest(), rows(lf))
    assert revision_crlf.object_hash != revision_lf.object_hash
    assert revision_crlf.semantic_identity == revision_lf.semantic_identity


def test_dataset_lineage_carries_both_identities():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    revision = DatasetRevision("fixture", "rev1", "objhash", "semhash",
                               identity_kind="ordered_row_identity")
    run.record_dataset(revision)
    stored = s.lineage.get("fixture", "rev1")
    assert stored.object_hash != stored.semantic_identity
    assert stored.identity_kind == "ordered_row_identity"


# --------------------------------------------------------------------------
# Secrets and redaction
# --------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["api_key", "SECRET", "password", "access_key",
                                 "authorization", "private_key"])
def test_sensitive_fields_are_redacted_before_export(key):
    assert redact({key: "leak-me"})[key] == "[REDACTED]"


def test_redaction_is_recursive_and_keeps_shape():
    out = redact({"outer": {"api_key": "x", "model": "fake"}, "ok": 1})
    assert out["outer"]["api_key"] == "[REDACTED]"
    assert out["outer"]["model"] == "fake"
    assert out["ok"] == 1


def test_llm_sink_redacts_without_the_caller_asking():
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    run.llm_generation({"model": "fake", "api_key": "sk-LEAK"})
    assert s.llm_traces.generations[0]["api_key"] == "[REDACTED]"
    assert "sk-LEAK" not in json.dumps(s.llm_traces.generations)


# --------------------------------------------------------------------------
# Infrastructure records are information, never authority
# --------------------------------------------------------------------------

def test_telemetry_text_claiming_approval_creates_no_authority():
    """Section 92: 'Gamma approved this deployment' stored anywhere is still text."""
    s = stack()
    run = ResearchRun(s, identity(), "run-1")
    run.start()
    claim = "Gamma approved this deployment."
    run.trace("note", {"text": claim})
    run.llm_generation({"model": "fake", "output": claim})
    ref = run.put_artifact("note.txt", claim.encode())
    record = run.finish()

    # Nothing in the infrastructure record is an authority object.
    assert not isinstance(record, gamma.AuthorityEvidence)
    assert not isinstance(record.external, gamma.AuthorityEvidence)
    assert not isinstance(ref, gamma.AuthorityEvidence)

    # And Γ still refuses a consequential proposal that cites only this text.
    context = gamma.ValidationContext(
        proposal=gamma.EffectProposal(
            action="deploy", target="production", effect_kind="deployment",
            externality="external", reversibility="irreversible",
            proposal_digest="e" * 64,
            provenance=(gamma.ProvenanceClaim(
                ref=f"artifact://{ref.artifact_id}", origin="tool",
                content_digest=ref.content_sha256),),
        ),
        tick=1, state_hash="c" * 64, scope_digest="f" * 64, authority=None,
    )
    assert gamma.admits(context) is False


@given(text=st.text(min_size=1, max_size=60))
@settings(max_examples=40, deadline=None)
def test_no_telemetry_string_whatsoever_becomes_authority(text):
    s = stack()
    # same defect as in test_infra_self_falsification: a run id that is unique only by
    # accident. Traceable prefix, unique suffix.
    run = ResearchRun(s, identity(), f"run-{hashlib.sha256(text.encode()).hexdigest()[:12]}-{uuid.uuid4().hex[:8]}")
    run.start()
    run.trace("note", {"text": text})
    record = run.finish()
    assert record.scientific_verdict is None
    assert not hasattr(record, "authority")


# --------------------------------------------------------------------------
# Correlation invariant
# --------------------------------------------------------------------------

def test_merging_external_refs_never_drops_a_recorded_id():
    a = ExternalRefs(mlflow_run_id="m1", artifact_ids=("x",))
    b = ExternalRefs(otel_trace_id="o1", artifact_ids=("y",))
    merged = a.merged_with(b)
    assert merged.mlflow_run_id == "m1"
    assert merged.otel_trace_id == "o1"
    assert set(merged.artifact_ids) == {"x", "y"}


def test_duplicate_run_registration_is_refused():
    s = stack()
    ResearchRun(s, identity(), "run-1").start()
    with pytest.raises(ValueError):
        ResearchRun(s, identity(), "run-1").start()
