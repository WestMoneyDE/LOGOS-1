# Research OS — Phase 3 und Phase 4 (design)

**Founder-Auftrag 2026-09-19 (nach R3):** „phase 3-4 ausarbeiten" mit vier Bausteinen — Erkenntnisse + Registerpflege, Prior-Art-Matrix per Deep Research, Agenten-Qualität (Evals), Publikationspfad — **plus** „Tracing von MLflow und Langfuse und weitere Tracing-Systeme für dieses Projekt mit ins Dashboard einfügen". Kein Dauerbetrieb/Zeitplan (Forschung läuft nur, wenn der Founder sie einschaltet). Reihenfolge: nach Abhängigkeiten, von mir festgelegt und hier begründet.

## 0. Reihenfolge und Begründung
| Runde | Inhalt | Warum hier |
|---|---|---|
| **Phase 3 = R4** | (a) Beobachtung: MLflow + Langfuse + OTel + Playwright-QA + Lab-Health in einer Ansicht, jeder Lauf mit allen Spuren; (b) Erkenntnis-Ansicht „Was wissen wir jetzt?"; (c) Registerpflege: geführter Weg vom Verdict-Entwurf zur tatsächlichen Registeränderung mit Diff und Founder-Freigabe | Beobachtung ist Voraussetzung, um allem anderen zu trauen (und unabhängig von allem). Erkenntnisse und Registerpflege bauen nur auf dem, was R1–R3 schon erzeugen (Register, Closures, Verdict-Entwürfe). Ohne Registerpflege bleibt jedes spätere Ergebnis ein Entwurf ohne Weg ins Register. |
| **Phase 4 = R5** | (d) Prior-Art-Matrix per Deep Research (24 offene Rechercheaufgaben → Briefs → Founder-Merge → Register); (e) Agenten-Qualität: Eval-Harness mit Gold-Beispielen + Benchmark-Modi mit echten Zahlen; (f) Publikationspfad: Paper-Entwurf aus Evidenz, Zahlen mit KI, Zitate, Limitationen, Export | Prior Art braucht den Merge-Pfad aus R4 (Registerpflege). Evals brauchen Agentenläufe **und** den Merge-Pfad, um Befunde festzuhalten. Der Publikationspfad braucht beides: belastbare Zitate und belastbare Zahlen. Innerhalb R5 daher in dieser Reihenfolge. |

## 1. Unverändert (Governance)
Founder-Gates bleiben; Agenten ändern **nie** ein Register, keinen Claim-Status, keine Evidenzstärke; Messläufe weiter `json` ohne `--verbose`, Cap 1; Agenten-Jobs Cap 3; `USAGE_LIMIT_REACHED` → STOP. Neu und ausdrücklich: **die Registerpflege ist eine Founder-Aktion im Werkzeug**, kein Automatismus — jede Änderung entsteht aus einem Entwurf, wird als Diff gezeigt, vom Founder bestätigt, gegen die Integritätsregeln geprüft (`registries.validate`, Status ≠ Evidenzstärke, Vokabular, Artefaktpflicht) und in `ros_audit` + einem Änderungsprotokoll festgehalten. Schlägt die Prüfung fehl, wird nichts geschrieben.

## 2. Phase 3 — Beobachtung (a)
Eine Seite `/observability` und ein Panel je Lauf:
- **Systeme**: Postgres (Lab), MinIO, MLflow, Langfuse, OTel-Collector, Docker-Worker, Host-Executor, Playwright-QA — je Zeile Zustand, Version/Endpoint, letzte Aktivität, Link. Zustand kommt aus den vorhandenen `health()`-Adaptern; ein nicht erreichbares System ist *nicht erreichbar*, nie „ok".
- **MLflow**: Experiment `logos-research-os` über die REST-API (Runs, Parameter, Metriken, Artefaktnamen) serverseitig gelesen und als Tabelle/Balken gezeigt; Deep-Link in die MLflow-UI.
- **Langfuse**: Traces/Generations des Projekts serverseitig über die lokalen Keys gelesen (Keys bleiben im Server, nie im Browser), gezeigt mit Modell, Tokens, Latenz, Verknüpfung zum Run; Deep-Link.
- **OTel**: Spans je Lauf aus `ros_trace_links` + Collector-zPages-Link; der Collector exportiert lokal (debug), deshalb steht ehrlich dort, dass Spans nur im Collector-Log liegen.
- **Playwright-QA**: letzte Matrix, Verstöße, Screenshots (vorhandene `/api/qa/last-run`).
- **Je Lauf** (`/traces/[run]`): ein Block „Alle Spuren" mit MLflow-Run, Langfuse-Trace, OTel-Trace-IDs, Artefakten, Worktree-Branch und Commit.

## 3. Phase 3 — Erkenntnisse (b)
`/insights`: „Was wissen wir jetzt?" in einfacher Sprache, mechanisch aus Records erzeugt (kein KI-Text):
- je Claim ein Satz nach Schablone: *„<Titel>: <Status> mit <Evidenzstärke> Evidenz, geprüft in <n> Experimenten, zuletzt <Datum>. Widerlegen würde: <Falsifikationstest>."*
- Gruppen: **gestützt**, **widerlegt/negativ**, **offen**, **blockiert**; je Eintrag Belege (Artefakt-Hash, Closure, Messlauf) und ein „Warum sicher/unsicher"-Hinweis aus Evidenzstärke + Replikationsstand.
- **Neu gelernt** (letzte 30 Tage) aus Closures, Messläufen, Radar-Annahmen.
- Jede Zahl mit n; keine Prozentwerte ohne Nenner; Verweis „Status ≠ Evidenzstärke" bleibt sichtbar.

## 4. Phase 3 — Registerpflege (c)
`control/registry_edit.py` + `/registry`:
1. Quelle: Verdict-Entwurf, Radar-Draft oder Messlauf.
2. **Vorschlag** (mechanisch): welches Feld welchen Registers würde sich ändern (`claims[].status`, `evidence_strength`, `supporting_artifacts`, `counterevidence`, `next_falsification_test`; `replication[].count`; `experiments[]` Eintrag; `negative_results`), inklusive Begründungspflicht.
3. **Diff-Ansicht** BEFORE/AFTER je Feld, plus Integritätsprüfung vorab (`registries.validate` auf dem geänderten Zustand, Vokabular, Status-vs-Stärke-Regel, Artefaktpflicht, verbotene Wörter).
4. 🔒 **Founder bestätigt** → Datei wird geschrieben (ein Feld je Änderung, kein Massen-Update), `ros_audit` + `docs/research/dashboard/registry-changelog.jsonl` (Zeile mit Zeitstempel, Quelle, Feld, vorher/nachher, Hash der Datei vorher/nachher).
5. Rückgängig: der Changelog erlaubt einen Revert-Vorschlag (ebenfalls mit Founder-Bestätigung), nie automatisch.
6. Agenten-Actor wird auf API-Ebene abgelehnt (`GovernanceError`), Tests beweisen es.

## 5. Phase 4 — Prior-Art-Matrix (d)
- Job `prior_art` erweitert: Aufgabenliste aus `research_intake.queue()`; der Agent nutzt `deep-research` / `scientific-thinking-literature-review`; Ergebnis ist ein Brief nach `BRIEF_SCHEMA` **plus** eine Matrixzeile (Track × Kriterium).
- `/prior-art` bekommt die **Matrix**: Tracks × (Zitatzahl, Neuheitsstatus, letzte Recherche, offene Aufgaben) mit Ampel, und je Claim „nächstgelegene Arbeit" — leer bleibt leer, nie erfunden.
- Merge über den Registerpflege-Pfad aus R4 (Founder-Freigabe, Novelty nie über `CLEAR_DIFFERENTIATION`).

## 6. Phase 4 — Agenten-Qualität (e)
- **Gold-Beispiele**: `docs/research/dashboard/evals/<stage>/*.json` — für jede Agentenstufe (TRIAGE, QUESTION, HYPOTHESIS, METRICS, PREREG) ein erwartetes Ergebnisprofil mit deterministischen Prüfungen (Pflichtfelder vorhanden, Falsifikationskriterium messbar formuliert, Metriken auf Scorer abbildbar, keine Statusaussage, keine erfundenen Zitate).
- **Eval-Job** (deterministisch, Docker-Worker): prüft die letzten Agentenausgaben gegen die Gold-Profile → Rate je Stufe mit Wilson-KI → `ros_metric_results` (Suite `AGENT_QUALITY`).
- **Benchmark-Modi mit echten Zahlen**: `LOGOS_AGENT` = Agent mit Packet/Skills, `BASELINE_AGENT` = derselbe Job ohne Packet-Kontext (nur Frage), beides über den vorhandenen Messpfad; `NO_DATA` verschwindet erst, wenn ein Lauf existiert.
- Ergebnis erscheint in `/benchmarks` und `/insights`.

## 7. Phase 4 — Publikationspfad (f)
- `control/paper.py`: aus `PUBLICATION-REGISTRY`, Claims, Experimenten, Messläufen, Prior Art und Evidenzschuld einen **Manuskript-Entwurf** erzeugen: Gliederung, Beitragssätze, Zahlen mit KI und n, Limitationen aus `known_limitations` + `evidence_debt`, Related Work aus dem Prior-Art-Register, „Does not claim"-Abschnitt aus P7 und den Integritätsregeln. Nur Records, keine erfundenen Sätze; leere Abschnitte bleiben als `TO_BE_WRITTEN` stehen.
- `/publications/[paper]/draft`: Entwurf lesen, Markdown exportieren (`docs/research/dashboard/paper-drafts/<paper>.md`), Reifegrad bleibt Founder-Entscheidung; ein Entwurf ändert nie `manuscript_status`.

## 8. Tests
R4: Health-Aggregation (jedes System einzeln nicht erreichbar → „unreachable", nie „ok"), MLflow-/Langfuse-Leser mit Fake-Clients (Keys nie im Response), Insights-Sätze (Schablone, exakte Gruppierung, n), Registerpflege (Vorschlag, Diff, Integritätsverletzung blockiert Schreiben, Agent abgelehnt, Changelog-Zeile, Revert-Vorschlag), Playwright (Observability-Seite, Insights, Registry-Diff mit Founder-Knopf).
R5: Matrix-Ableitung, Brief→Merge über Registerpflege, Eval-Profile (Gold-Beispiele, Rate mit KI), Baseline-vs-Agent-Messlauf, Paper-Entwurf (nur Records, `TO_BE_WRITTEN` bleibt stehen).

## 9. Außerhalb des Umfangs
Zeitgesteuerter Dauerbetrieb; automatische Registeränderung; KI-generierte Fließtexte in Papers; externe Replikation durch Dritte; Änderung der Messlauf-Grenze.
