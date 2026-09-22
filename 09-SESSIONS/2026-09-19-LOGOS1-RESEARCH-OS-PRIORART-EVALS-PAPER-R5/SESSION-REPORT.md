# SESSION REPORT — LOGOS1-RESEARCH-OS-PRIORART-EVALS-PAPER-R5 (Phase 4 von „Phase 3-4")

**Kind:** tooling; kein wissenschaftlicher Status geändert; kein Modellaufruf
**Base:** `3c483e2` (R4) · branch `tooling/logos-dashboard-part1` · PR #34 · date 2026-09-19
**Verdict:** `RESEARCH_OS_R5_PRIORART_EVALS_PAPER_BUILT`

## 1. Gebaut (Reihenfolge d → e → f: Zitate vor Zahlen vor Text)
- **Literatur-Matrix** (`prior_art.py`, `/prior-art/matrix`): Track × (Quellen, Neuheitsverteilung, offene Aufgaben, letzte Recherche, Ampel). Heute: 14 Quellen, **vier Spuren rot, zwei gelb, keine grün** — die Neuheit ist für keinen Claim belegt, und genau das steht dort. Je Claim die nächstliegenden Arbeiten und ein Neuheitssatz, der „nicht belegt" sagt, wenn nichts belegt ist. „Recherche beauftragen" reiht einen `prior_art`-Agentenjob mit genau einer Aufgabe aus der 24er-Warteschlange ein (Start bleibt Founder-Klick).
- **Brief-Merge**: Diff vor dem Schreiben (neue Zitate, Duplikate, Novelty-Deckelung), 🔒 Founder-Aktion; der Klick **ist** die Prüfung und wird als `reviewed_by_founder` + Zeitpunkt in die Brief-Datei geschrieben; Eintrag im Registry-Changelog mit Dateihash vorher/nachher; `CLEAR_DIFFERENTIATION` mit weniger als drei Quellen wird abgelehnt; Agenten bekommen `GovernanceError` (API 403).
- **Agenten-Qualität** (`evals.py`, `/evals`): sechs Stufen, je vier deterministische Prüfungen (Substanz, keine Statusaussage, Record-Verweise, messbares Falsifikationskriterium, H0/H1, Frage + Abgrenzung, Metriken auf vorhandene Scorer abbildbar, Prereg-Pflichtfelder, Quellenpflicht). **Kein LLM-Judge.** Raten mit Wilson; nicht bewertbar zählt als fehlend. Aggregat schreibbar in `ros_metric_results` (Suite `AGENT_QUALITY`) und damit sichtbar im Benchmark-Labor.
- **Publikationspfad** (`paper.py`, `/publications/[id]/draft`): Manuskript-Entwurf aus Records — Beiträge (mit Status *und* Evidenzstärke), verwandte Arbeiten je Track inkl. Lücke, Methoden mit Experiment-IDs/Prereg/Artefakt-Hashes, Ergebnisse (Messläufe mit n und KI; sonst der ehrliche Satz „kein governed Messlauf"), Negativergebnisse, Limitationen, Evidenzschuld, „Was dieses Papier nicht behauptet", Reproduzierbarkeit, offene Blocker, Kriterienstand. Abstract bleibt `TO_BE_WRITTEN`; **`manuscript_status` wird nie geändert** (Test prüft es). Export nach `docs/research/dashboard/paper-drafts/<PAPER>.md` + `.json`, deterministischer sha256.

## 2. Zahlen
pytest **4376 passed, 2 skipped** (Kontrollebene 53 Tests); Playwright **350 passed** auf 6 Viewports. Claude-Aufrufe durch diesen Auftrag: **0**. Registerdateien nach den Tests byte-genau wie vorher (Hygiene im Test erzwungen).

## 2a. Nebenbefund behoben: die QA-Erfassung war kaputt
Der Playwright-Routen-Report (`/system/qa`) wurde von parallelen Workern mit Lesen-Ändern-Schreiben auf **eine** Datei geschrieben. Ergebnis: eine 1,7 MB grosse, ungültige JSON-Datei (`Extra data`), und zuvor unbemerkt unvollständige Matrizen. Behoben an der Ursache: ein Shard **je Worker** (`route-inventory.<projekt>.w<n>.json`), ein `globalSetup`, das die Shards des Vorlaufs löscht, und ein Leser, der alle Shards zusammenführt und eine kaputte Datei als `broken_shards` meldet statt den Endpunkt zu killen. Nachher: 323 Routenprüfungen über alle sechs Viewports, 0 Verstösse, 0 kaputte Shards.

## 3. Was diese Runde bewusst nicht tut
Keine automatische Registeränderung (auch nicht bei Prior Art); keine LLM-Bewertung von Agentenarbeit; kein generierter Fließtext im Paper; kein Reifegrad-Upgrade; keine externe Replikation.

## 4. Offen
Erster echter Agenten-/Messlauf weiterhin ausstehend; Benchmark-Definitionen DRAFT; `--resume` unentschieden; die Literatur-Matrix bleibt rot, bis echte Deep-Research-Läufe Quellen liefern. Kettenkopf unverändert: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
