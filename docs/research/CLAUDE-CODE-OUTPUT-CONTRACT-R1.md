# Claude Code structured-output contract — as used by the LOGOS-1 result-model resolver (R1)

**Order:** `COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1` · **Repair prereg:** `ded746c0…` · **Claude Code version validated:** `2.1.275` · **Resolver contract version:** `cc-result-model/1`
**Sources (official, fetched 2026-09-18):** `code.claude.com/docs/en/headless` (Run Claude Code programmatically) and `code.claude.com/docs/en/agent-sdk/typescript` (SDK message types). Everything under "documented" below is quoted from those pages; everything under "observed" comes from the captured raw invocation of the invalid run (`5f887962…`) and carries **no contractual semantics**.

## 1. Documented `--output-format json` result envelope (`SDKResultMessage`)

Success arm: `type: "result"`, `subtype: "success"`, `uuid`, `session_id`, `duration_ms`, `duration_api_ms`, `is_error`, `api_error_status?`, `num_turns`, `result`, `stop_reason`, `total_cost_usd`, `usage`, `modelUsage: { [modelName: string]: ModelUsage }`, `permission_denials`, optional `structured_output`, `terminal_reason`, `fast_mode_state`, ….
Error arm: `subtype` ∈ {`error_max_turns`, `error_during_execution`, `error_max_budget_usd`, `error_max_structured_output_retries`}, `is_error`, `errors: string[]`, `startup_failure_reason?`, `modelUsage`, ….
"When a failure happens inside the run, such as missing authentication, Claude Code prints the failure as the result on stdout." Exit code 0 on success, non-zero on failure; invalid flags are reported to stderr before the run.

`ModelUsage` = `inputTokens, outputTokens, thinkingTokens?, cacheReadInputTokens, cacheCreationInputTokens, webSearchRequests, costUSD, contextWindow, maxOutputTokens, canonicalModel?, provider?, costBasis?`. `costUSD`/`total_cost_usd` are **client-side estimates**, not a bill.

**Documented semantics of `modelUsage`:** "per-model totals for every model call made through the query pipeline … including the main loop, subagents, and internal calls such as compaction and Workflow agents." → auxiliary entries are *expected*; **no ordering semantics are documented**; the map does not say which entry produced `result`.
**Documented semantics of `usage`:** "main agent loop only. Excludes subagent and auxiliary model calls." → `usage` corroborates the main-loop token count but is not keyed by model.

## 2. Documented `--output-format stream-json` lifecycle

`system/init` (first event unless startup events precede it; fields include `model` = the session's selected model, `tools`, `mcp_servers`, `plugins`, …) → `assistant` / `user` messages → final `result` message (same envelope as §1). `SDKAssistantMessage` = `type: "assistant"`, `uuid`, `session_id`, `message: BetaMessage` ("includes fields like `id`, `content`, `model`, `stop_reason`, and `usage`"), `parent_tool_use_id` (`null` for the main conversation), optional `error` ∈ {`authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`, `billing_error`, `rate_limit`, `overloaded`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `cloud_credential_error`, `unknown`}. `system/api_retry` events carry `error` (same categories) and `error_status`.

→ **The response-producing model is documented at Tier 1:** the `message.model` of the main-conversation assistant message(s) (`parent_tool_use_id == null`) that carry the final text.

## 3. Documented `--model` / bare mode / fallback

`--model <model>`: alias for the latest model (`fable`, `opus`, `sonnet`) or a full name. `--fallback-model`: automatic fallback when the default model is overloaded/unavailable — **forbidden** under `FALLBACK_PROVIDER = NONE`. `--bare`: skips CLAUDE.md / plugins / hooks / MCP / auto memory but "doesn't use your subscription login" (needs `ANTHROPIC_API_KEY`) — **not usable** under the Max-subscription-only governance. Without `--bare`, `-p` "loads the same context an interactive session would, including anything configured in the working directory or `~/.claude`."

## 4. Field classification used by the resolver

| field | status | resolver use |
|---|---|---|
| `assistant.message.model` (stream-json, `parent_tool_use_id == null`) | documented (BetaMessage) | **Tier 1** explicit producer |
| top-level result producer field | **none documented** in 2.1.275 | Tier 2 never fires (`CONTRACT_UNSUPPORTED` if configured) |
| `modelUsage` keys / `canonicalModel` | documented as per-model totals incl. auxiliary calls; **order undocumented** | **Tier 3** containment only (pin present ⇒ `REQUEST_PIN_PLUS_USAGE_CONTAINMENT`, weaker evidence); never ordering |
| `system/init.model` | documented (session model) | requested-selector check (must equal the pin) |
| `result`, `is_error`, `subtype`, `api_error_status`, `errors`, assistant `error`, `api_retry.error` | documented | status classifier `cc-status/2` |
| `usage.*`, `cache_creation_input_tokens` | documented (main loop only) | scaffolding/context metrics (aggregate; no decomposition claimed) |
| `inference_geo`, `service_tier`, `speed`, `fast_mode_state` | observed in 2.1.275 output | recorded only; `inference_geo = not_available` ⇒ region NOT ASSUMED |

## 5. Invariants

`AuxiliaryModelUsage != PrimaryResponseModel` · `ModelUsagePresence != ResultProducerIdentity` · map key order is never model-identity evidence · ambiguity fails closed (`AMBIGUOUS` → not accepted) · auxiliary usage is audited separately and never merged into the producer field.
