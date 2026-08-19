# LOGOS-1 Session Persistence Protocol

Every substantive LOGOS-1 research/engineering session must leave a durable GitHub checkpoint.

## Required per session

Create a session directory under `09-SESSIONS/<SESSION-ID>/` and preserve, as applicable:

1. `SESSION-REPORT.md` — objective, work performed, results and scope;
2. raw experiment/result artifacts or content-addressed references to them;
3. evidence delta — what was strengthened, weakened, rejected, merged or left unresolved;
4. open blockers / unanswered questions;
5. provenance — input parent, source pins, hashes and relevant runtime state;
6. next work order.

## Canonical-state rule

Update root `CURRENT-WORK-ORDER.md`, `00-MAIN-STATE/CURRENT-STATE.md` and the progress index only when the canonical state actually changes.

Historical session results are append-only. Do not overwrite older evidence to make a later conclusion look cleaner.

## Scientific-state rule

A session report is not itself scientific promotion.

Promotion still requires the applicable LOGOS evidence-maturity gate, frozen falsifier/baseline contracts and raw evidence. Resource/transport failure remains `UNTESTED`.

## Cross-chat continuity

GitHub is the durable continuity layer for session progress. A new chat/session should read the latest canonical state and the most recent session report before starting new work.
