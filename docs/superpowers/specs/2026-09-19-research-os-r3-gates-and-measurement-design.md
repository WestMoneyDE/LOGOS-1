# Research OS R3 — Von der Prereg zum Messlauf (design)

**Order:** LOGOS1-RESEARCH-OS-MEASUREMENT-R3 (founder request 2026-09-19, after R2). Base: `fba27a0`.

## 0. Founder decisions (brainstorm 2026-09-19)
1. **Weg über die Gates bis zum Messlauf** ist der Schwerpunkt: Prereg einfrieren → Work Order freigeben → Trockenlauf → echter governed Messlauf → Ergebnis + Verdict-Vorschlag. Jeder Gate-Schritt ist ein Founder-Klick mit Erklärung in einfacher Sprache.
2. **Messläufe dürfen aus dem Dashboard gestartet werden** — nur mit eingefrorener Prereg, freigegebener Work Order, bestandenem Trockenlauf und Caps aus dem Governance-Record. Messläufe laufen über `ClaudeCodeMaxProvider` mit `--output-format json` **ohne** `--verbose` (Amendment R1 gilt nur für Agenten-Jobs).
3. **Cap für Agenten-Jobs auf 3** (nur `thesis_advance`, `prior_art`, `radar_process`); **Messläufe bleiben bei 1**. Wird als Founder-Amendment `INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1` eingetragen (`max_concurrent_sessions` im Record bleibt die Messlauf-Grenze).
4. **Desktop-Benachrichtigungen im Browser**, lokal, ohne externen Dienst: wartendes Gate, fertiger Lauf, Quota-Stopp.

## 1. Was unverändert bleibt
Subscription-only; kein API-Key; Founder-Gates bleiben Founder-Gates; `USAGE_LIMIT_REACHED` → STOP; Agenten dürfen weiterhin keine Register ändern, keine Prereg einfrieren, keinen Verdict setzen. Neu ist nur, dass der Founder diese Schritte **im Dashboard** auslösen kann statt per Skript — mit denselben Prüfungen wie im Skript-Pfad (`logos_research.governance.validate_run_preregistration`, `dry_run_contract`, Aktivierungstoken v2, Zählerprüfungen).

## 2. Messlauf-Vertrag `ros-measurement/1` (prereg-getrieben, experimentunabhängig)
Der Agent legt im Thesenverzeichnis drei Dateien an (Stufe `METRICS_DEFINED` → `PREREG_DRAFT`), die zusammen den Messlauf definieren:

| Datei | Inhalt |
|---|---|
| `DATASET.json` | `{schema: "ros-dataset/1", items: [{item_id, arm, input, expected, meta}], arms: [...]}`; balanciert über Arme, Hash = sha256 des kanonischen JSON |
| `PROMPTS.json` | `{schema: "ros-prompts/1", arms: {<arm>: {system, user_template}}}`; `user_template` nutzt `{input}` und darf keine Antwort verraten |
| `MEASUREMENT.json` | `{schema: "ros-measurement/1", metrics: [{metric_id, scorer, arm, target_field}], primary_metric, comparison: {arm_a, arm_b}, falsification: {rule, threshold}, caps: {max_invocations, max_turns, max_output_bytes, timeout_s}, invalid_measurement_criteria: [...]}` |

**Scorer-Bibliothek** (deterministisch, im Repository, keine LLM-Bewertung): `exact_match`, `normalized_match`, `contains_all`, `json_field_equals`, `json_field_in`, `regex_match`, `refusal`, `parse_failure`. Jeder Scorer liefert `True | False | None` (None = nicht auswertbar → Missingness, nie als Erfolg gezählt).

**Falsifikationsregeln**: `difference_ci_excludes_zero` (Newcombe-KI von Arm A − Arm B schließt 0 aus, Richtung geprüft), `rate_below_threshold`, `rate_above_threshold`. Der Verdict-Vorschlag ergibt sich mechanisch aus der eingefrorenen Regel — nicht aus einer Bewertung.

## 3. Gate-Kette im Dashboard (jede Stufe eigener Endpoint + Karte)
1. **Prereg prüfen** (`POST /api/ros/theses/{id}/prereg/validate`): baut aus `PREREG-DRAFT.json` + `MEASUREMENT.json` + `DATASET.json` die stochastische Prereg (`stochastic_preregistration`), prüft mit `validate_run_preregistration(payload, gov)` und listet jeden Verstoß in einfacher Sprache mit Regelnamen. Keine Änderung.
2. **Prereg einfrieren** 🔒 (`POST …/prereg/freeze`): friert im Labor-Postgres ein (`repository.freeze_preregistration`, Identity aus git-SHA + Γ-Version + Dataset-Hash), schreibt Hash in `ros_theses.prereg_hash` und in die Work Order, Thesis → `PREREG_FROZEN`. Idempotent; ein geänderter Inhalt erzeugt einen neuen Hash, nie eine Überschreibung.
3. **Work Order freigeben** 🔒 (bestehend): DRAFT → APPROVED mit Prereg-Hash; Thesis → `WORK_ORDER_READY`.
4. **Trockenlauf** (`POST …/dry-run`, deterministischer Worker-Job `dry_run`): prüft die zehn `DRY_RUN_CHECKS` gegen die eingefrorene Prereg (Metadaten, Pins, Privacy, Kostenkonto, Metriken auflösbar, Artefaktpfade, Provenance-Graph, Trajektorien-Capture, Invalidierungsregeln, Forbidden-Provider-Guard) — **null Modellaufrufe**, Zähler bleiben 0. Ergebnis über `dry_run_contract`; Thesis → `DRY_RUN`, bei Fehlschlag → `BLOCKED_BY_GOVERNANCE` mit Liste.
5. **Messlauf freigeben** 🔒 (`ready_to_run`) und **starten** (`POST …/measurement/start`): Job `measurement` (Claude-Kind, cap 1), Founder-Start mit Gate-Snapshot.
6. **Messlauf** (`control/measurement.py`): Aktivierungstoken v2 (CLI-Version, Vertrag, Dataset-Hash, Prompt-Bundle-Hash), Budget = Items × Arme + Retry-Reserve ≤ `max_invocations`, pro Item eine Invocation über `ClaudeCodeMaxProvider` (json), Ergebnis → Scorer → `ros_measurement_items`; Abbruch bei Cap, `USAGE_LIMIT_REACHED`, Modell-Drift, Dataset-Drift, Prompt-Drift (→ `INVALID_MEASUREMENT`). Live-Fortschritt als Run-Events (`measure.item`, alle 5 Items aggregiert).
7. **Ergebnis** (`control/verdict.py`): Raten je Arm mit Wilson, Differenz mit Newcombe, Missingness, dann die eingefrorene Falsifikationsregel → Vorschlag `SUPPORTED | FALSIFIED | INCONCLUSIVE | INVALID_MEASUREMENT` + Begründungssatz. Founder entscheidet 🔒 (`POST …/verdict/decide`); erst dann Thesis → `VERDICT`/`FALSIFIED` und ein **Registry-Update-Entwurf** (`docs/research/dashboard/verdict-drafts/<thesis>.json`) mit BEFORE/PROPOSED/EVIDENCE — nie eine automatische Registeränderung.

## 4. Datenmodell (Migration v4)
`ros_measurements` (measurement_id, thesis_id, work_order_id, run_id, prereg_hash, dataset_hash, prompt_bundle_hash, model_pin, state, planned, executed, invalid_reason, started, finished, summary jsonb) · `ros_measurement_items` (measurement_id, item_id, arm, invocation, status, raw_sha256, parsed jsonb, score bool|null, latency_s, tokens jsonb, at) · `ros_theses.prereg_hash` · `ros_gate_log` (thesis_id, gate, actor, passed, detail, at) — die Gate-Kette als eigener Lesepfad für die UI.

## 5. UI
- **Thesen-Workspace**: neue Karte „Weg zur Messung" mit fünf Schritten, je Schritt Zustand (offen/geprüft/erledigt), Erklärsatz, Button (🔒 wo Founder), und bei Fehlschlag die Liste in einfacher Sprache.
- **Messlauf-Ansicht** `/measurements/[id]`: Fortschrittsbalken (n von N), Raten je Arm mit Wilson-KI live, Missingness, Abbruchgrund, Item-Tabelle (Status/Score), Verdict-Vorschlag mit der eingefrorenen Regel und den zwei Buttons.
- **Leitstand**: Thesen-Karten zeigen die Gate-Kette kompakt; Benachrichtigungen (Browser-Notification) bei wartendem Gate, fertigem Lauf, Quota-Stopp — opt-in per Schalter, Erlaubnis wird im Browser abgefragt.
- **Statistik**: Messläufe erscheinen in `/traces` (Tokens, Dauer) und als eigene Karte „Messläufe" mit n.

## 6. Tests
Scorer-Bibliothek (Tabellen-Tests, None-Semantik), Falsifikationsregeln (KI-Grenzen, Richtung), Prereg-Bau + Validierung (jede Governance-Regel einzeln verletzt), Freeze-Idempotenz gegen das echte Labor-Postgres, Trockenlauf-Vertrag (Zähler 0), Messlauf mit Fake-Runner (Budget, Cap-Stopp, Usage-Limit, Drift, Missingness, exakte Item-Zahlen), Verdict-Ableitung (alle vier Ausgänge), Gate-Endpunkte (Actor-Gates), Cap-Amendment (Agenten 3, Messlauf 1 — Governor-Test), Playwright (Gate-Karte, Messlauf-Seite mit Fake-Messung, Benachrichtigungsschalter).

## 7. Außerhalb des Umfangs
LLM-Bewertung von Antworten; automatische Registeränderung; Mehrfach-Messläufe parallel; Replikation externer Labore; Änderung der Messlauf-Grenze (bleibt 1).
