# Research OS R5 (Phase 4) — Prior-Art-Matrix, Agenten-Qualität, Publikationspfad

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (d) die Literaturlage belastbar machen (Matrix + Deep-Research-Jobs + Merge über die Registerpflege), (e) die Qualität der Agentenarbeit messbar machen (Gold-Profile, Eval-Job, echte Benchmark-Modi), (f) aus dem Evidenzstand einen Paper-Entwurf erzeugen, der nur Records zitiert. Spec: `docs/superpowers/specs/2026-09-19-research-os-phase3-4-design.md` §5–§7.

## Global Constraints
- Reihenfolge innerhalb R5: **d → e → f** (Zitate vor Zahlen vor Text).
- Agenten erzeugen Briefs und Entwürfe; **Register ändert nur der Founder** über den R4-Pfad (`registry_edit`), inklusive Prior-Art-Merge; Novelty nie über `CLEAR_DIFFERENTIATION`.
- Evals sind deterministisch (Profilprüfungen), kein LLM-Judge; Raten mit Wilson; `NO_DATA` bleibt stehen, solange kein Lauf existiert.
- Der Paper-Entwurf schreibt **keinen** Fließtext, den kein Record deckt: leere Abschnitte bleiben `TO_BE_WRITTEN`; `manuscript_status` wird nie verändert.
- Tests deterministisch mit exakten Zahlen; keine Netzaufrufe in Tests; TEST-ROS-Reste entfernt.

### Task 1 (d): `prior_art.py` — Matrix je Track (Zitate, Novelty, offene Aufgaben, letzte Recherche), Brief-Validierung, Merge-Vorschläge über `registry_edit`; API `/api/ros/prior-art/*`; Prior-Art-Job-Payload aus `research_intake.queue()`.
### Task 2 (e): `evals.py` — Gold-Profile je Agentenstufe, deterministische Prüfungen, Eval-Job im Worker (Suite `AGENT_QUALITY`), Raten mit Wilson in `ros_metric_results`; API `/api/ros/evals/*`.
### Task 3 (e): Benchmark-Modi mit echten Zahlen — `LOGOS_AGENT` vs `BASELINE_AGENT` über den Messpfad (gleiche Prereg, unterschiedlicher Packet-Kontext), Eintrag in `benchlab`.
### Task 4 (f): `paper.py` — Manuskript-Entwurf aus Records (Gliederung, Beiträge, Zahlen mit KI, Related Work, Limitationen, „Does not claim"), Export nach `docs/research/dashboard/paper-drafts/<paper>.md`; API `/api/ros/papers/*`.
### Task 5: UI — `/prior-art` Matrix, `/evals`, `/publications/[paper]/draft`; Playwright.
### Task 6: Gate — pytest, Playwright, Klassifikation, Closure, Commit, Push.
