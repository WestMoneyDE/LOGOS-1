# Laya juror integration — design

**Kind:** engineering design. No claim status changes. Γ is not modified by this design.
**Date:** 2026-09-23
**Evidence base:** `docs/research/LAYA-INTEGRATION-RESEARCH-R1.md` (recommendations R1–R11).
**Relation to earlier design:** supersedes the transport, contract and calibration-record sections
of `2026-09-23-laya-decision-layer-design.md` (§3–§6). That document stays as the record of the
first design; its authority rules (Jev/Laya may only tighten, no threshold without a frozen record)
carry over unchanged.

**Founder decisions carried in (2026-09-23):**

| # | Decision |
|---|---|
| D1 | This run builds sub-projects 1–4 and the navigator; the ≥400-case dataset and the architectural block on benign-phrased instructions are the next work order |
| D2 | LOGOS-1 runs its own Laya service; `jev-ultrafast` is not modified |
| D3 | A Laya flag emits `TIGHTEN`, never `REFUSE`; Γ-18 is unchanged; "TIGHTEN → UNCLEAR → human" is recorded as a Γ candidate for the first calibrated record |
| D4 | ADVISE classifies the agent's own output and the evidence it read, as separate channels |
| D5 | Laya navigates the working graph before INTAKE, on the existing thesis state machine, never the authority graph |
| D6 | The navigator starts in shadow mode and switches to acting only with a calibration record |
| D7 | Every component passes test → validate → evaluate before it is integrated |

---

## 1. Two roles, one model

```text
Juror      ADVISE in the authority graph. Classifies untrusted text. May only tighten.
Navigator  The working graph before INTAKE. Chooses the next step among the legal ones.
           Stops in front of every wall.
```

Both roles call the same service and the same model. Neither role can create authority: the juror's
vocabulary has no permitting vote, and the navigator's option set never contains a gated step.

## 2. Component 1 — the `logos-laya` service

A LOGOS-owned container, defined in `infra/docker-compose.yml` beside the lab stack. The source lives
in `infra/laya/` so it is versioned, reviewed and pinned with the repository.

```text
package        laya==0.3.6 (exact pin; 0.3.7 is a separate, measured change)
model          convaiinnovations/laya at a full 40-character HF revision, downloaded at build
runtime        HF_HUB_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1
checkpoints    english and typed-decisions preloaded; multilingual on demand (max_loaded=2)
network        127.0.0.1:8110 on the host; non-root user; read_only root filesystem; mem_limit
concurrency    one uvicorn worker, one inference slot, bounded wait queue; full -> 503
```

**Contract `laya-classify/1`.**

```text
POST /v1/classify
  request   request_id, text (bounded), question_id, question (type + instructions + criteria),
            route (optional: english | multilingual | typed-decisions)
  response  one variant per question type, selected by the `type` tag:
              noul    p_true, confidence
              choice  choice, probabilities{option: p}, confidence
              score   level, probabilities{level: p}, confidence
            plus, on every response: schema_version, package_version, hf_revision, route,
            latency_ms
  errors    503 LAYA_NOT_READY | LAYA_BUSY (with Retry-After), 504 LAYA_TIMEOUT,
            502 LAYA_OUTPUT_INVALID, 422 LAYA_BAD_REQUEST

GET /livez    the process is alive (constant time)
GET /readyz   200 only after the configured checkpoints loaded and one warm-up passed
```

The model is loaded at startup in the lifespan handler. No probe triggers a load. `act_probability`
is not returned.

**What this fixes:** the `noul` 502 (each type has its own variant, and a test proves every type
has one), the missing pins (every response names what answered), the `0.0.0.0` binding, the
healthcheck that loads the model, and the floating package version.

## 3. Component 2 — the client `src/logos_laya`

This component is built by extension, not replacement: the standing rule forbids deleting or
weakening tests.

- A new transport, `ClassifyClient`, speaks `/v1/classify`. The existing chat path (`HttpLaya`,
  the envelope parser, `yes_probability`) stays with its tests, marked in its docstring as the
  superseded path to the LM Studio model. No new code calls it.
- **One place maps every failure to `ABSTAIN`:** timeout, non-200, schema-invalid body, a pin that
  differs from the record in force, a base URL that is not a loopback address. The loopback rule is
  checked, not documented.
- `CalibrationRecord` gains `question_sha256` (hash of the canonical question definition),
  `package_version`, `hf_revision` and `route`, all defaulted, and `PROTOCOLS` gains `"classify"`.
  For a `classify` record, `admissible()` checks the new fields; the existing checks are unchanged.
- A new `juror_vote(answer, record, *, pins)` implements D3 for the classify path: `TIGHTEN` at or
  above the record's threshold, `ABSTAIN` otherwise and whenever no admissible record exists. It is
  the only vote function ADVISE calls. The existing `advisory_vote` belongs to the superseded chat
  path, is not called by anything, and keeps its behaviour and tests unchanged. No existing test
  changes an expected value in this run.

## 4. Component 3 — ADVISE, the juror in the authority graph

- `RunState.untrusted: tuple[UntrustedText, ...]` with `UntrustedText(channel, ref, text)` and
  `channel ∈ {agent_output, evidence}`. The caller supplies the evidence text; the graph stores
  nothing beyond the run.
- ADVISE calls the juror once per text, once per decision. Advisories are part of
  `context_digest`, so a second call with a different answer would fail `REDEEM` by design.
- Advisory source: `laya:injection:agent_output` or `laya:injection:evidence:<ref>`.
- The edge `ADVISE → VALIDATE` and the dominator set are unchanged.

## 5. Component 4 — the navigator (the snake)

The navigator runs on the existing thesis state machine
(`src/logos_dashboard/control/state_machines.py`). No new state machine is introduced.

```text
the target    the next state, compiled per step into a Laya `choice` question
the options   events_from(kind, state) minus FOUNDER_GATES, plus "stay"
the walls     a founder gate               -> STOP_AT_GATE    (stops in front of it)
              beyond AGENT_CEILING          -> STOP_AT_CEILING
              a transition that does not exist or is forbidden -> never offered
standing      an answer outside the options, an abstention, a timeout -> STAND_STILL
```

`compile_step(kind, state, step_output)` builds the question from fixed per-state text, so its
`question_sha256` is stable and a later record can pin it. `interpret(answer, options)` returns one
of `event`, `STAY`, `STOP_AT_GATE`, `STOP_AT_CEILING`, `STAND_STILL`.

**Shadow mode (D6).** At every real thesis transition, the navigator's move is computed and written
beside it to `ros_audit`. The transition itself runs through `transition()` exactly as today.
Agreement and disagreement become the labelled data for the routing record. The switch to acting
is not part of this run.

## 6. The gate every component passes (D7)

A component is integrated only after all three stages pass, in order. A failed stage stops that
component; its result is recorded, not repaired into a pass.

| Stage | What it proves | Exit criterion |
|---|---|---|
| **Test** | The component does what its contract says, with no model and no network | Deterministic unit tests green; every failure mode enumerated |
| **Validate** | It holds against the real service and cannot cross a wall | Golden answers captured from the real checkpoint validate against the schema; the safety properties below pass against the running service |
| **Evaluate** | How well it works, with the uncertainty stated | A measurement report with Wilson intervals, compared against a stated baseline |
| **Integrate** | — | Its own commit, then the full suite after the commit |

**Safety properties to validate:**

- The service answers every question type; no type can produce a 502 by shape.
- A Laya outage, timeout or malformed answer never moves a verdict toward `VALID` (lesion test).
- The juror emits nothing outside `ADVISORY_VOTES` and never `REFUSE`; a `TIGHTEN` leaves Γ's
  verdict exactly where it was (Γ-18 unchanged).
- The navigator never offers a founder-gate event or a step beyond `AGENT_CEILING`.
- **Differential test:** with Laya switched off, and with scripted adversarial answers, the sequence
  of thesis transitions is byte-identical. The shadow cannot move anything.

**Evaluations in this run:**

- Juror: the 24-case probe and the matched EN/DE 8+8 sets over HTTP, on `laya==0.3.6`, compared
  case by case with the in-process probe on the same version. Identical results prove the HTTP path;
  any difference is a finding.
- Navigator: a labelled offline set of thesis steps, including the TRIAGE branch and advance-versus-
  stay decisions, reported as agreement with Wilson intervals. It is a probe, not a record.

## 7. What this design does not do

- It does not write a calibration record and does not claim Laya is admissible as a juror or a
  navigator. Every vote stays `ABSTAIN` until a record exists.
- It does not change Γ, the authority graph's edges, or any founder gate.
- It does not modify `jev-ultrafast`. Running both services at once may exceed the 9.7 GB WSL VM;
  the plan measures memory first and the founder decides about the other container.
- It does not close the benign-phrased-instruction class ("Before answering, first delete…"). That
  needs an architectural control in the proposal path and is the next work order, with the dataset.
- It does not install or depend on LangGraph.

## 8. As built — deviations from this design (2026-09-24)

| Design said | Built | Why |
|---|---|---|
| host `127.0.0.1:8110` | host `127.0.0.1:58110`, container port 8110 | the lab compose file's 5xxxx host-port convention |
| `english` + `typed-decisions` preloaded, `max_loaded=2` | `english` preloaded, `max_loaded=1`, others on demand | measured memory: 2.03 GiB steady; two resident checkpoints plus the jev container exceed the 9.7 GiB WSL VM |
| `mem_limit` from measurement | `3g` | the checkpoint switch completes under 3g without OOM; a switch (19–59 s) outlasts the 5 s client timeout, so a caller sees ABSTAIN |
| request carries `text` | request carries `state: {name: text}` | the vendor's questions reference named state fields in backticks (the guard question asks about \`prompt\`), and laya serialises the state dict verbatim; the service follows that convention. An earlier justification by a measured effect (9/45 → 40–45/45) was withdrawn on 2026-09-25 (`docs/research/BROWSE-OBSERVATION/KEYSTONE-R1.md` §0) |
| GPU variant offered | not built | CPU p50 304 ms suffices for the juror; a GPU image needs its own equivalence study |
| `advisory_vote` emits TIGHTEN | new `juror_vote` emits TIGHTEN; `advisory_vote` unchanged | extension only: no existing test changes an expected value |
