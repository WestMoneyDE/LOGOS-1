# Research OS R4 (Phase 3) — Beobachtung, Erkenntnisse, Registerpflege

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (a) alle Spuren eines Laufs an einem Ort (MLflow, Langfuse, OTel, Artefakte, QA, Lab-Health), (b) eine Seite, die in einfacher Sprache sagt, was das System weiß, (c) der geführte, geprüfte Weg vom Entwurf zur tatsächlichen Registeränderung mit Founder-Freigabe. Spec: `docs/superpowers/specs/2026-09-19-research-os-phase3-4-design.md`.

## Global Constraints
- Keys (Langfuse) bleiben serverseitig; die API liefert nie Schlüssel an den Browser.
- Ein nicht erreichbares System wird als *unreachable* gemeldet, nie als „ok"; Fehler degradieren die Ansicht, brechen sie nicht.
- Registeränderungen: nur `actor == "founder"`, nur ein Feld je Vorgang, Integritätsprüfung **vor** dem Schreiben, Changelog-Zeile + Audit; Agenten werden abgelehnt.
- Insights-Texte sind Schablonen über Records — kein generierter Fließtext, keine Zahl ohne n.
- Tests deterministisch mit exakten Zahlen; Fake-Clients für MLflow/Langfuse; TEST-ROS-Reste werden entfernt.

### Task 1: `control/observe.py` — Systemzustände + MLflow/Langfuse-Leser (Fake-fähig), `/api/ros/observability`, `/api/ros/runs/{id}/all-traces`
### Task 2: `insights.py` — mechanische Erkenntnissätze, Gruppen, „neu gelernt", `/api/ros/insights`
### Task 3: `control/registry_edit.py` — Vorschlag, Diff, Integritätsprüfung, Founder-Schreibpfad, Changelog, Revert-Vorschlag; `/api/ros/registry/*`
### Task 4: UI — `/observability`, `/insights`, `/registry`, Lauf-Panel „Alle Spuren", Leitstand-Verweise; Playwright
### Task 5: Gate — pytest, Playwright, Klassifikation, Commit, Push
