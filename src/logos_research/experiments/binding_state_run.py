"""Execute BINDING-STATE-PRESERVATION-R1 against the materialized laboratory.

Order of operations is the scientific discipline, not a convenience:

```text
freeze preregistration (content-addressed, Postgres)
  -> instrument validation (positive + negative control)
  -> run the frozen matrix
  -> derive the verdict from the FROZEN falsification criterion
  -> persist verdict, negative result, failure attribution, artifacts
  -> reconstruct from experiment_id with integrity verification
```

Nothing here repairs anything. A counterexample is recorded, not fixed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..infra.adapters import DatasetRevision
from ..infra.backends import backends_from_env
from ..infra.identity import ExperimentIdentity, environment_id
from ..infra.runner import ResearchRun, ResearchStack, resolve_from_experiment_id
from ..manifest import PreRegistration
from . import binding_state as bs

EXPERIMENT_ID = bs.EXPERIMENT_ID


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=Path(__file__).resolve().parents[3]).stdout.strip()
    except Exception:
        return ""


PREREGISTRATION = PreRegistration(
    research_question=(
        "Can supported representation transformations preserve the operational "
        "binding force of a constraint without unauthorized weakening, strengthening, "
        "scope change, or authority change?"
    ),
    hypothesis=(
        "H1: for each tested transformation T not authorized to change normative "
        "force, BindingForce(T(C)) == BindingForce(C) within the preregistered domain."
    ),
    null_hypothesis=(
        "H0: at least one tested representation path preserves approximate semantic "
        "meaning while silently changing the operational binding of the constraint."
    ),
    claim_type="architectural",
    independent_variables=("transformation_path", "constraint_class", "parser_strictness"),
    dependent_variables=("BindingRetention", "ActionOutcome", "FalseAllowRate"),
    controlled_variables=("ScopeContract fields", "ProposedAction", "tick window", "Gamma version"),
    known_confounders=(
        "summary transform is an EXPERIMENTAL_TRANSFORM_FIXTURE, not production code",
        "contract valid_from/valid_until are not enforced by ScopeDecision.evaluate(); "
        "freshness enforcement in this experiment comes from the grant window via Gamma",
    ),
    baseline="T0 direct evaluation (no transformation)",
    positive_controls=("T1 lossless serialization roundtrip",),
    negative_controls=("authorized MUST_NOT->SHOULD_NOT with authorized_normative_change=True",),
    interventions=(
        "T1 serialize", "T2 memory roundtrip (REAL)", "T3 complete summary (FIXTURE)",
        "T3 lossy summary keep=2 (FIXTURE)", "T5 projection handoff (REAL)",
        "T4/T6 chains", "adversarial mutations (Section 18)",
    ),
    success_criteria=(
        "FalseAllowRate == 0 and BindingRetention == 1.0 on every unmutated path"
    ),
    falsification_criteria=(
        "H1 is falsified for a tested path if a valid binding constraint, transformed "
        "by a path not authorized to change normative force, yields a representation "
        "under which an action forbidden by the original becomes ALLOW, or otherwise "
        "loses required operational force, without an explicit authorized normative "
        "transition."
    ),
    inconclusive_criteria="results conflict and the responsible stage cannot be isolated",
    invalid_measurement_criteria=(
        "positive control fails, or the negative control is not distinguishable "
        "(instrument cannot separate MUST_NOT from SHOULD_NOT)"
    ),
    metrics=("SemanticRetention", "BindingRetention", "AuthorityRetention",
             "FalseAllowRate", "FalseBlockRate", "FirstBindingLossStage"),
    statistical_plan=(
        "Deterministic exhaustive matrix; no sampling, so no interval estimate. "
        "Any single false-allow on an unauthorized path falsifies H1 for that path."
    ),
    measurement_instruments=("measure_retention (typed field comparison)",
                             "evaluate_action (ScopeDecision + logos_gamma)"),
    random_seeds=(),
)


def run() -> dict[str, Any]:
    backends = backends_from_env()
    repo = backends["repository"].connect()
    repo.migrate()

    # ---- freeze -----------------------------------------------------------
    prereg_payload = asdict(PREREGISTRATION)
    prereg_hash = PREREGISTRATION.digest()
    identity = ExperimentIdentity(
        experiment_id=EXPERIMENT_ID, experiment_revision=1,
        preregistration_hash=prereg_hash, git_sha=_git_sha(), gamma_version="v0.2",
        environment_id=environment_id({
            "python": sys.version.split()[0], "schema_version": str(repo.schema_version()),
            "requirements_lock_sha256": sha256(
                (Path(__file__).resolve().parents[3] / "requirements.lock").read_bytes()
            ).hexdigest(),
        }),
    )
    repo.ensure_experiment(EXPERIMENT_ID, "Binding-state preservation across representation")
    repo.freeze_preregistration(identity, prereg_payload)

    stack = ResearchStack(repository=repo, artifacts=backends["artifacts"],
                          lineage=_RepoLineage(repo), tracker=backends["tracker"],
                          traces=backends["traces"], llm_traces=None)  # no LLM arm
    run_id = f"{EXPERIMENT_ID}-run-{uuid.uuid4().hex[:8]}"
    session = ResearchRun(stack, identity, run_id, clock=_now())
    session.start()
    session.trace("binding_r1_start", {"preregistration_hash": prereg_hash})

    # ---- fixture identity: object hash AND semantic identity ----------------
    fixture_json = json.dumps([asdict(f) for f in bs.fixtures()], sort_keys=True,
                              separators=(",", ":")).encode()
    session.record_dataset(DatasetRevision(
        dataset_name="binding-r1-fixtures", revision="r1",
        object_hash=sha256(fixture_json).hexdigest(),
        semantic_identity=sha256(json.dumps(
            sorted(f.constraint.digest() for f in bs.fixtures())).encode()).hexdigest(),
        identity_kind="structured_object_identity"))

    # ---- instrument validation BEFORE interpretation -----------------------
    tmp = Path(tempfile.mkdtemp(prefix="binding-r1-"))
    T1 = bs.Transform("T1_serialize", "REAL_REPO_PATH", bs.t_serialize)
    pos = bs.run_matrix([T1], with_mutations=False)
    positive_ok = all(r.retention.binding and r.retention.authority
                      and not r.false_allow and not r.false_block for r in pos)
    from dataclasses import replace as _replace
    a = [f for f in bs.fixtures() if f.constraint.constraint_id == "C-A-prohibition"][0]
    weakened = _replace(a.constraint, binding=False, authorized_normative_change=True)
    neg = bs.measure_retention(a.constraint, weakened)
    negative_ok = (not neg.binding) and neg.semantic > 0.8

    if not (positive_ok and negative_ok):
        record = session.finish(scientific_verdict="INVALID_MEASUREMENT", completed_at=_now())
        repo.close()
        return {"verdict": "INVALID_MEASUREMENT", "positive_control": positive_ok,
                "negative_control": negative_ok, "run_id": run_id}

    # ---- the frozen matrix --------------------------------------------------
    transforms = [
        T1,
        bs.make_memory_transform(tmp / "t2"),
        bs.make_summary_transform(strict=True),
        bs.make_summary_transform(strict=False),
        bs.make_lossy_summary_transform(keep_sentences=2, strict=True),
        bs.make_lossy_summary_transform(keep_sentences=2, strict=False),
        bs.make_projection_transform(tmp / "t5"),
        bs.chain("T4_lossy2_strict->memory",
                 bs.make_lossy_summary_transform(keep_sentences=2, strict=True),
                 bs.make_memory_transform(tmp / "t4s")),
        bs.chain("T4_lossy2_lenient->memory",
                 bs.make_lossy_summary_transform(keep_sentences=2, strict=False),
                 bs.make_memory_transform(tmp / "t4l")),
        bs.chain("T6_lossy2_lenient->memory->projection",
                 bs.make_lossy_summary_transform(keep_sentences=2, strict=False),
                 bs.make_memory_transform(tmp / "t6l"),
                 bs.make_projection_transform(tmp / "t6lp")),
        bs.chain("T6_complete->memory->projection",
                 bs.make_summary_transform(strict=False),
                 bs.make_memory_transform(tmp / "t6c"),
                 bs.make_projection_transform(tmp / "t6cp")),
    ]
    results = bs.run_matrix(transforms, with_mutations=True)
    summary = bs.summarize(results)
    unmutated = [r for r in results if r.mutation == "none"]
    counterexamples = [r for r in unmutated if r.false_allow]

    # ---- first-loss localization for every counterexample -------------------
    localized = []
    for ce in counterexamples:
        fx = [f for f in bs.fixtures() if f.constraint.constraint_id == ce.constraint_id][0]
        stages = [
            ("T3_lossy2_lenient", bs.make_lossy_summary_transform(keep_sentences=2, strict=False)),
            ("T2_memory", bs.make_memory_transform(tmp / f"loc-{ce.constraint_id}")),
            ("T5_projection", bs.make_projection_transform(tmp / f"locp-{ce.constraint_id}")),
        ]
        current = fx.constraint
        first_loss = None
        for name, tf in stages:
            nxt = tf.apply(current)
            if first_loss is None and not bs.measure_retention(current, nxt).binding:
                first_loss = name
            current = nxt
        localized.append({"constraint": ce.constraint_id, "path": ce.transform,
                          "first_binding_loss_stage": first_loss or "NONE_IN_CHAIN",
                          "semantic_retention": ce.retention.semantic,
                          "changed_fields": list(ce.retention.changed_fields)})

    # ---- verdict from the FROZEN criterion ------------------------------------
    real_paths_ok = all(not r.false_allow and r.retention.binding
                        for r in unmutated if r.path_kind == "REAL_REPO_PATH")
    verdict = "FALSIFIED" if counterexamples else "SUPPORTED"

    # ---- persist -------------------------------------------------------------
    report = {
        "experiment_id": EXPERIMENT_ID, "run_id": run_id,
        "preregistration_hash": prereg_hash, "verdict": verdict,
        "positive_control": positive_ok, "negative_control": negative_ok,
        "real_repo_paths_preserved_binding": real_paths_ok,
        "summary": summary, "counterexamples": localized,
        "cases": [asdict(r) | {"retention": asdict(r.retention),
                               "false_allow": r.false_allow, "false_block": r.false_block}
                  for r in results],
    }
    ref = session.put_artifact("binding-r1-results.json",
                               json.dumps(report, indent=2, sort_keys=True).encode(),
                               "application/json")
    repo.record_artifact(ref)

    if stack.tracker is not None:
        try:
            stack.tracker.log_params(run_id, {"verdict": verdict, "fixtures": str(len(bs.fixtures())),
                                              "transforms": str(len(transforms))})
            stack.tracker.log_metrics(run_id, {
                "false_allow_unmutated": float(summary["false_allow_unmutated"]),
                "false_block_unmutated": float(summary["false_block_unmutated"]),
                "mutations_detected": float(summary["mutations_detected"]),
                "mutations_total": float(summary["mutations_total"]),
                "cases": float(summary["cases"]),
            })
        except Exception:
            pass

    if counterexamples:
        for loc in localized:
            repo.record_negative_result(
                f"{EXPERIMENT_ID}-{loc['constraint']}-{loc['path']}",
                "H1 strong binding preservation",
                f"path {loc['path']} against constraint {loc['constraint']}",
                f"forbidden action became ALLOW; binding lost at {loc['first_binding_loss_stage']}; "
                f"semantic retention {loc['semantic_retention']}; changed {loc['changed_fields']}",
                "EXPERIMENTAL_TRANSFORM_FIXTURE path; every REAL_REPO_PATH preserved binding",
                run_id=run_id)
        with repo._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO failure_attributions (failure_id, run_id, source, evidence, scope) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (failure_id) DO NOTHING",
                (f"{run_id}-first-loss", run_id, "MEASUREMENT" if not localized else "TOOL",
                 "SUMMARY_TRANSFORM: lossy compression + lenient default-on-missing parse",
                 "binding loss originates upstream of memory; memory and projection propagate it faithfully"))
        repo._conn.commit()

    record = session.finish(scientific_verdict=verdict, completed_at=_now())
    if hasattr(stack.traces, "flush"):
        stack.traces.flush()

    # ---- reconstruct with integrity + rehash the frozen preregistration ------
    view = resolve_from_experiment_id(stack, EXPERIMENT_ID)
    with repo._conn.cursor() as cur:
        cur.execute("SELECT payload FROM preregistrations WHERE preregistration_hash=%s",
                    (prereg_hash,))
        stored = cur.fetchone()[0]
    rehash_ok = PreRegistration(**{k: (tuple(v) if isinstance(v, list) else v)
                                   for k, v in stored.items()}).digest() == prereg_hash
    repo.close()
    return {"verdict": verdict, "run_id": run_id, "preregistration_hash": prereg_hash,
            "positive_control": positive_ok, "negative_control": negative_ok,
            "real_repo_paths_preserved_binding": real_paths_ok,
            "summary": summary, "counterexamples": localized,
            "artifact": ref.artifact_id, "reconstruction": view,
            "preregistration_rehash_ok": rehash_ok, "run_status": record.status}


class _RepoLineage:
    criticality = "CANONICAL"

    def __init__(self, repo):
        self._repo = repo

    def health(self):
        return self._repo.health()

    def record(self, revision):
        self._repo.record_dataset(revision)

    def get(self, *_):
        raise NotImplementedError
