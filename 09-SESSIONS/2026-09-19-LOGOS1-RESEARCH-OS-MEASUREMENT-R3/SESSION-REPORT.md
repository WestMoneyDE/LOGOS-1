# SESSION REPORT — LOGOS1-RESEARCH-OS-MEASUREMENT-R3

**Kind:** tooling + measurement pipeline + one founder governance amendment; no scientific status changed; no governed measurement executed (runner proven with fake runners)
**Base:** `fba27a0` (R2 closure) · branch `tooling/logos-dashboard-part1` · PR #34 · date 2026-09-19
**Verdict:** `RESEARCH_OS_R3_MEASUREMENT_PATH_BUILT`

## 1. Founder decisions (brainstorm)
Weg über die Gates bis zum Messlauf · Messläufe aus dem Dashboard startbar (Founder-Start, eingefrorene Prereg, Caps) · Agenten-Parallelität auf 3, Messläufe bleiben bei 1 · Browser-Benachrichtigungen. Spec: `docs/superpowers/specs/2026-09-19-research-os-r3-gates-and-measurement-design.md`, Plan: `docs/superpowers/plans/2026-09-19-research-os-r3-measurement.md`.

## 2. Governance amendment (founder, recorded)
`docs/research/INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1.json`: `max_parallel_agent_sessions = 3` für Agenten-Jobs; `max_concurrent_sessions = 1` aus dem Governance-Record bleibt die Messlauf-Grenze, und während ein Messlauf läuft, wird **kein** Agenten-Job disponiert (`MEASUREMENT_RUNNING`). Durchgesetzt in `governor.can_dispatch`; Änderung nur durch den Founder (1..5).

## 3. Gebaut
- **Messvertrag `ros-measurement/1`** (`measurement_contract.py`): DATASET/PROMPTS/MEASUREMENT-Schemata, kanonische Hashes, acht deterministische Scorer (`exact_match` … `parse_failure`, `None` = nicht bewertbar), drei eingefrorene Falsifikationsregeln, mechanische Verdict-Ableitung (SUPPORTED/FALSIFIED/INCONCLUSIVE/INVALID_MEASUREMENT) mit Wilson/Newcombe. Kein LLM-Judge.
- **Gate-Kette** (`control/prereg.py`): Prereg aus den Agenten-Dateien bauen → `governance.validate_run_preregistration` (dieselbe Funktion wie im Skriptpfad) → 🔒 einfrieren im Labor-Postgres (`freeze_preregistration`, Hash = Primärschlüssel) → Work Order freigeben → Trockenlauf mit den zehn `DRY_RUN_CHECKS` **ohne einen Modellaufruf** (Delta-Zählerprüfung) → 🔒 Messlauf freigeben. Jeder Versuch in `ros_gate_log`.
- **Messlauf** (`control/measurement.py`): Aktivierungstoken v2 (CLI, Vertrag, Dataset-/Prompt-Hash), Budget, ein `claude -p --output-format json` je Datenpunkt (ohne `--verbose`), deterministische Bewertung, Live-Events alle 5 Items, Stopp bei Cap, Quota, Modell-Drift, Auth-Drift, Founder-Stop; `ros_measurements` + `ros_measurement_items`; Telemetrie-Spiegel + Artefakt.
- **Verdict**: Vorschlag aus der eingefrorenen Regel; 🔒 Founder entscheidet; Ergebnis wird als `verdict-drafts/<these>-<messlauf>.json` mit BEFORE/PROPOSED/EVIDENCE/WHY/WHAT-WOULD-FALSIFY-IT abgelegt — **nie** eine Registeränderung.
- **UI**: Gate-Karte „Weg zur Messung" im Thesen-Workspace (sieben Schritte, 🔒-Markierung, Klartext-Fehlerlisten, Trockenlauf-Checkliste), `/measurements` + `/measurements/[id]` (Fortschritt, Quoten je Arm mit Wilson-KI als Balken, Missingness, Item-Tabelle mit Antworten, Vorschlag + vier Entscheidungsknöpfe), Browser-Benachrichtigungen (lokal, opt-in), Leitstand zeigt Agenten- und Messlauf-Grenzen getrennt.
- **Robustheit**: Detailseiten unterscheiden jetzt 503 (records-only), 404 (nicht vorhanden) und Fehler — vorher 500.

## 4. Zahlen
pytest **4365 passed, 2 skipped** (ein bekannter Vorgänger-Flake `test_infra_self_falsification` einmal rot, auf Rerun grün — `hash(lie) % 10000` Run-ID-Kollision, nicht von diesem Auftrag verursacht und nicht verändert). Control-Plane-Suite **43 Tests**. Playwright **311 passed** auf 6 Viewports. Claude-Inferenzaufrufe durch diesen Auftrag: **0** (Fake-Runner; die Zähler in der Suite stammen aus ihnen).

## 5. Offen
1. Erster echter Agentenlauf und erster echter Messlauf stehen weiterhin aus (Founder-Klicks + Host-Daemon).
2. Benchmark-Definitionen weiterhin DRAFT.
3. `--resume` weiterhin unentschieden.
4. Kettenkopf unverändert: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
