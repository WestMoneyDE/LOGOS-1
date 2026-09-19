# SESSION REPORT — LOGOS1-RESEARCH-OS-OBSERVE-INSIGHTS-REGISTRY-R4 (Phase 3 von „Phase 3-4")

**Kind:** tooling + Registerpflege-Werkzeug; kein wissenschaftlicher Status geändert; kein Modellaufruf
**Base:** `acfbe39` (R3) · branch `tooling/logos-dashboard-part1` · PR #34 · date 2026-09-19
**Verdict:** `RESEARCH_OS_R4_OBSERVE_INSIGHTS_REGISTRY_BUILT`

## 1. Auftrag und Reihenfolge
Founder: „phase 3-4 ausarbeiten" mit vier Bausteinen + Tracing-Integration, kein Dauerbetrieb, Reihenfolge nach Abhängigkeiten. Spec beider Phasen: `docs/superpowers/specs/2026-09-19-research-os-phase3-4-design.md` (§0 begründet die Reihenfolge). **Phase 3 = R4** (diese Sitzung): Beobachtung, Erkenntnisse, Registerpflege — weil Beobachtung Voraussetzung für Vertrauen in alles Weitere ist und ohne Registerpflege jedes spätere Ergebnis ein Entwurf ohne Weg ins Register bliebe. **Phase 4 = R5**: Prior-Art-Matrix, Agenten-Evals, Publikationspfad (in dieser Reihenfolge, weil jeder Schritt den vorherigen braucht).

## 2. Gebaut
- **Beobachtung** (`control/observe.py`, `/observability`): acht Systeme mit ehrlichem Zustand (MLflow, Langfuse, OTel-Collector, Labor-Postgres, MinIO, Host-Executor, Docker-Worker, Claude-Auth) — *nicht erreichbar* heißt nicht erreichbar; MLflow-Läufe (Parameter, Metriken, Deep-Link) und Langfuse-Traces serverseitig gelesen, **Zugangsschlüssel verlassen den Server nie** (Test prüft es); OTel ehrlich als „Debug-Exporter, Spans nur im Collector-Log"; je Lauf ein Block „Alle Spuren" (MLflow-Run, Langfuse-Trace, OTel-IDs, Artefakte, Branch/Commit, degradierte Telemetrie).
- **Erkenntnisse** (`insights.py`, `/insights`): 23 Claims in vier Gruppen (gestützt 16 · widerlegt 2 · offen 5 · blockiert 0), je ein Satz aus Register-Feldern nach fester Schablone plus „Wie sicher?"-Hinweis (Fixture-Grenze, fehlende Replikation, Gegenbefunde). Claims↔Experimente über die Invarianten des Tracks — dieselbe Regel wie die Claim-Detailseite; wo kein Experiment hängt, steht das auch so da (P7). „Neu gelernt (30 Tage)" aus Closures und Messläufen.
- **Registerpflege** (`control/registry_edit.py`, `/registry`): Vorschlag (aus Verdict-Entwürfen) → Diff BEFORE/AFTER je Feld → Integritätsprüfung auf dem geänderten Zustand → 🔒 Founder bestätigt → genau ein Feld wird geschrieben, mit Dateihash vorher/nachher, Zeile in `registry-changelog.jsonl` und `ros_audit`. Geprüft werden: Begründungspflicht, Status-Vokabular, **Status verlangt Mindest-Evidenzstärke** (SUPPORTED ≥ MEDIUM), Artefaktpflicht, höchstens eine Stufe Evidenzsprung, `registries.validate` auf dem geänderten Register. Agent-Actor wird mit `GovernanceError` abgelehnt (API 403). Rücknahme gibt es nur als Vorschlag.

## 3. Zahlen
pytest **4371 passed, 2 skipped** (Kontrollebene 48 Tests). Playwright **332 passed** auf 6 Viewports. Claude-Aufrufe durch diesen Auftrag: **0**.

## 4. Registrierte Erweiterungen an Vorgängertests (nur Registrierung, nichts geschwächt)
- `test_ZERO_inference_proof`: `logos_dashboard/control/observe.py` ist neben `logos_research/infra` der zweite erlaubte Netz-Leser (nur Loopback-Telemetrie); die Modellanbieter-Prüfungen (openai/anthropic-Clients, `api.*`-Hosts) gelten unverändert auch für diese Datei.
- Diff-Scope-Test: Closure-/Sitzungsdateien von R3 und R4 eingetragen.
- `test_every_content_reader_is_classified`: statt einer Ausnahme wurde das Feld `source` der Registerpflege-API in `origin` umbenannt — es ist die Herkunft eines Vorschlags, kein Memory-Reader.

## 5. Offen
Erster echter Agenten-/Messlauf weiterhin ausstehend; Benchmark-Definitionen DRAFT; `--resume` unentschieden. Kettenkopf unverändert: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
