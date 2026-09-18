# MODEL_PIN_GATE — COGNITIVE-PROVENANCE-ABLATION-R1

**State:** `STOP — awaiting founder model selection` (Section 18, steps 5–6). No prompt has been submitted. `model_calls = provider_calls = claude_code_inference_invocations = 0`.
**Recorded:** 2026-09-18T16:24Z · branch `research/cognitive-provenance-ablation-r1` · base `52563dd` · setup preregistration `56ca6144499cd2126ec2180c338fec3e31762dc7a41157ef44acf8ec813834a9` (model pin deliberately not frozen)

## 1. Claude Code installed
`claude` on PATH (`~/.local/bin/claude`) · `claude --version` → **`2.1.275 (Claude Code)`** (documented command; no model; no inference).

## 2. Max-subscription auth evidence (documented `claude auth status --json`; no inference; identifiers redacted)
```text
loggedIn          = true
authMethod        = claude.ai
apiProvider       = firstParty        (not Bedrock / Vertex / Foundry)
subscriptionType  = max
status timestamp  = 2026-09-18T16:24Z
```
Redacted and NOT recorded: email, orgId, orgName, config paths. No token, cookie or credential was read, copied or stored. → **auth class = MAX_SUBSCRIPTION**, **subscription class = Max**, **AUTH_GATE = PASS (class-level evidence)**.

## 3. PAYG / API contamination check (presence only)
`ANTHROPIC_API_KEY` absent · `CLAUDE_CODE_USE_BEDROCK` absent · `CLAUDE_CODE_USE_VERTEX` absent · `CLAUDE_CODE_USE_FOUNDRY` absent (research shell environment). Console PAYG path: not in use (`apiProvider = firstParty`, `authMethod = claude.ai`). → clean.

## 4. Model choices exposed to the authenticated Max account
Claude Code 2.1.275 documents the `--model` flag as accepting **an alias for the latest model (`fable`, `opus`, `sonnet`) or a model's full name (e.g. `claude-fable-5`)**. There is no documented non-interactive command that enumerates the account's model list without opening a session, and opening a session is not a zero-inference action under this preregistration; the harness therefore does **not** enumerate or select. Suitable choices presented to the founder (single-shot JSON planning task, `--max-turns 1`, no tools):

| choice | selector to pin | note |
|---|---|---|
| Opus 5 | `claude-opus-5` (alias `opus`) | most capable general model; recommended if quota allows 156–180 short invocations |
| Sonnet 5 | `claude-sonnet-5` (alias `sonnet`) | faster / lighter on Max quota |
| Fable 5.1 | `claude-fable-5-1` (alias `fable`) | latest family per CLI help |

Pin rule: the founder names exactly **one** selector. A full model name is preferred over an alias (an alias may resolve to a different backend over time → `MODEL_VERSION_DRIFT`). The harness records `requested_model_selector` and the `reported/resolved model` from every invocation's JSON (`model` / `modelUsage`); any change → STOP. `backend_snapshot = NOT_EXPOSED` (Claude Code does not expose one).

## 5. Documented flags relevant to the boundary (from `claude --help`, 2.1.275)
Approved set only: `-p`, `--output-format json|stream-json`, `--model`, `--max-turns`, `--system-prompt`, `--append-system-prompt`, `--allowedTools`, `--disallowedTools`. Refused by `check_argv` (tested): `--fallback-model` (would enable automatic model fallback → forbidden under `FALLBACK_PROVIDER = NONE` / no silent model switch), `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, `--resume`, `--continue`, `--mcp-config`.

## 6. Gates before the pin
```text
METRIC_GATE               = PASS   (M10 CAUSALLY_DISCRIMINATED; M32/M33/M34 registered, CAUSALLY_DISCRIMINATED, fixture-scoped)
HARNESS_MUTANTS           = PASS   (15/15 caught, 0 surviving)
INSTRUMENT_FIRST          = PASS   (dataset, balance, leakage, parsers, construct gate, control mapping, provenance capture, counters, artifact writer)
AUTH_GATE                 = PASS   (class-level evidence above)
MODEL_PIN_GATE            = STOP   (founder selection required)
PREREG (run)              = PENDING (frozen after the pin: logos.stochastic-prereg/1 with cost_cap = 0, claude_max_limits)
ZERO_INFERENCE_PREFLIGHT  = PENDING (after the pin)
DRY_RUN                   = PENDING (after the pin)
```

## 7. Founder decision required (verbatim template)
```text
MODEL_PIN = <exactly one selector, e.g. claude-opus-5>
selection_owner = founder
selection_date  = <date>
```
The harness does nothing further until this is recorded here and in the run preregistration.
