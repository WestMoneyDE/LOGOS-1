# SESSION REPORT — LOGOS1-LAYA-JUROR-INTEGRATION-R1

**Kind:** engineering + measurement. Kein wissenschaftlicher Status geändert. Γ nicht verändert.
**Base:** `0e22425` · branch `main` · 2026-09-23 bis 2026-09-24
**Verdict:** `LAYA_JUROR_INTEGRATED_NOT_ADMISSIBLE`
**Founder-Entscheidungen (D1–D8):** Teilprojekte 1–4 jetzt, Datensatz und Architektur-Sperre als
Folgeauftrag · eigener LOGOS-Dienst, jev-ultrafast unangetastet · Laya sendet höchstens `TIGHTEN`,
Γ-18 unverändert · beide Eingabekanäle getrennt · Navigator auf der vorhandenen Thesen-Zustandsmaschine ·
Schattenmodus bis ein Record existiert · Test → Validate → Evaluate vor jedem Einbau · Browse-Use erst
auf Keystone, dann Injektionsseiten; Keystone-Tests später gestoppt · LLM-Ausgabe professionell und klar.
Ab dem Ziel „nichts fragen, nur validierte Empfehlungen" wurden alle weiteren Entscheidungen mit der
jeweils empfohlenen, an Messungen geprüften Option getroffen (§5).

## 1. Ergebnis

```text
Dienst      infra/laya: laya==0.3.6, HF-Revision 5e7b2b1b gepinnt, SHA256SUMS beim Build geprueft,
            offline zur Laufzeit, 127.0.0.1:58110, read-only, cap_drop ALL, mem_limit 3g, Profil `laya`.
            laya-classify/1: je Fragetyp eine Antwortvariante, Pins in jeder Antwort.
            noul p50 304 ms / p95 384 ms; choice p50 235 ms; 2,03 GiB dauerhaft.
Client      ClassifyClient: jeder Fehler -> ABSTAIN an einer Stelle, 20 Gruende; Loopback im Code
            erzwungen. juror_vote: nur TIGHTEN/ABSTAIN, liest p_true, nie `confidence`.
ADVISE      klassifiziert Agent-Ausgabe und jede Evidenz getrennt; fehlerhafter Advisor -> ABSTAIN;
            Topologie, Dominatoren, README-Diagramm byte-gleich.
Navigator   auf der Thesen-Zustandsmaschine; nie ein Founder-Gate, nie ueber AGENT_CEILING;
            Schattenmodus (LOGOS_LAYA_SHADOW=1) aendert per Differentialtest nichts (Laesion geprueft).
Record      keiner. Jede Juror-Stimme bleibt ABSTAIN, bis der Founder einen Record unterschreibt.
```

## 2. Befunde

**2a. „Laya" bezeichnete zwei Modelle.** Das Paket zielte auf das LM-Studio-Modell (Qwen 2B, Chat);
der Juror ist `convaiinnovations/laya` (ModernBERT-Klassifikator). Die Umbenennung vom Vortag hatte den
Namen korrigiert, nicht das Ziel. Jetzt spricht der Juror mit dem richtigen Modell; der alte Chat-Pfad
bleibt mit seinen Tests als überholt markiert.

**2b. jev-ultrafasts Laya-Wrapper verwarf jede Guard-Frage.** `_normalize` verlangte `probabilities`,
die `noul`-Antworten nie haben: jede Injektionsfrage gab 502. Der LOGOS-Dienst trennt die Antworttypen
und testet genau diese Fehlerklasse.

**2c. Warum jev-ultrafast abbricht — gemessen, nicht vermutet** (`docs/research/BROWSE-OBSERVATION/KEYSTONE-R1.md`).
72 Keystone-Aufgaben, jede mit Laya-Frage gescheitert. Ursachen der 69 Fehlschläge: 24 Planer macht aus
„klicke X" ein Formularfeld; 17 Ziel erreicht, nicht erkannt (Titel immer „Keystone", URL-Segment passt
nur zufällig — die zwei Treffer sind genau die zwei Erfolge); 15 Laya wählt falsch; 13 Ziel nie
angeboten. Laya ist Hauptursache in 22 %.

**2d. Zwei eigene Hypothesen widerlegt, eine bestätigt.** Positionsbias: widerlegt (Umkehr der
Reihenfolge ohne Effekt; das Muster kam von jevs Vorsortierung). Checkpoint oder kürzere Eingabe allein:
wirkungslos. Bestätigt: die Frageform. Laya klassifiziert einen Zustand mit benannten Feldern gegen eine
Frage, die sie in Backticks referenziert. Mit `state={"target"}` und „Which element opens \`target\`?"
steigt die Trefferquote auf den 45 geloggten Fragen von 9/45 auf 40/45 (English) und 45/45
(typed-decisions). Grenze: Soll-Labels aus dem Zieltext, Umschreibungen ungeprüft.

**2e. Das Modell änderte sich während der Sitzung.** Hugging Face veröffentlichte am 2026-09-23 die
Revision `aa8c91ca` ohne `multilingual`-Checkpoint; ein ungepinnter Replay lud sie in den Cache des
jev-Containers. Die Zahlen blieben gleich — aber genau dieser Fall ist der Grund für den Pin.

**2f. Deutsch ohne Umlaute wird auf den englischen Checkpoint geroutet** und dort verfehlt (p 0,10;
multilingual 0,934). Pflicht-Stratum im Folgeauftrag.

**2g. Ein eingefügter Beratungstext (≈250 000 Zeichen) wurde Behauptung für Behauptung geprüft.** Er
beschrieb überwiegend ein anderes Modell (verbalisierende LLMs), widersprach sich (Core ML in Docker)
und enthielt Code, der Erfolg unbedingt meldet. Übernommen: nur Evidence-Carrying Termination im Kern.

## 3. Messung (Phase 3/4)

Vollständig in `docs/research/LAYA-CALIBRATION/injection-NOT-ADMISSIBLE.md`; Rohdaten `measure-*.json`.

**Äquivalenz.** 513 (Text, Route)-Aufrufe über HTTP und in-process auf demselben gepinnten Image:
`p_true` identisch auf 4 Stellen, gleiche Route, max |Δ| = 0,0. Der HTTP-Pfad ist bewiesen.

**Injektionsfrage, 95-%-Wilson** (Auszug):

```text
Probe 24, Route auto/english   Schwelle 0,5  Recall 10/12 (0,55-0,95)  FPR 1/12 (0,02-0,35)
                               Schwelle 0,9  Recall  7/12              FPR 0/12 (0-0,24)
matched DE, Route english      Schwelle 0,5  Recall  4/8  (0,22-0,79)
matched DE, Route multilingual Schwelle 0,5  Recall  5/8  (0,31-0,86)
saubere Luecke                 in keinem Satz, auf keiner Route (AUROC 0,90-0,98)
```

**Falsch-Positive auf harmlosem Seitentext** (Keystone, 95 eindeutige Seitentexte, Route english):
34/95 = 0,36 (0,27–0,46) bei 0,5; 7/95 = 0,07 (0,04–0,14) bei 0,9. Die vollständigen Zustände mit der
`Goal:`-Zeile des Agenten werden in 99 von 167 Fällen markiert — die Aufgabe des Agenten *ist* eine
Anweisung. Das ist der Grund, warum ADVISE `agent_output` und `evidence` getrennt bewertet.

**Injektionsseiten** (27 Seiten, 21 mit Injektion): 7/21 erkannt bei 0,5 (0,17–0,55), 3/21 bei 0,9.
Indirekte und als Bitte formulierte Anweisungen je 1/4; Schmuggel (Nullbreiten-, Tag-Zeichen,
Homoglyphen) drückt denselben Payload von 0,92 auf 0,15 bzw. 0,0001. Harte Negative: 1/6 markiert.

**Einordnung.** Laya ordnet Injektionen im Mittel höher ein als harmlosen Text (AUROC ~0,9), trennt
sie aber an keiner Schwelle sauber, markiert ein Drittel harmloser Seiten und fällt auf Schmuggel
herein. Als Juror ist es nicht zulassungsfähig; die Architektur hält das aus, weil ohne Record jede
Stimme `ABSTAIN` ist. Grenzen: Angriffs- und Harmlos-Sätze stammen vom selben Agenten, der gemessen
hat; die deutschen Vergleichssätze sind neu verfasst, keine Replikation; Keystone ist eine App.

## 4. Übergabe außerhalb von LOGOS

Die Korrektur für jev-ultrafast (`docs/superpowers/specs/2026-09-23-jev-abort-fix-design.md`) ist
entworfen, validiert und an die Sitzung übergeben, die das Repo besitzt. Der Founder hat dort alle
jev-/Laya-Arbeit pausiert; **eingebaut ist sie nicht.** Die Keystone-Datenbank wurde nicht
zurückgespielt (10 von 18 Tabellen verändert, darunter ein Favorit aus einem Rateklick); die Liste und
die Sicherung stehen im Bericht.

## 5. Entscheidungen ohne Rückfrage (Ziel: nur validierte Empfehlungen)

| Frage | Entscheidung | Beleg |
|---|---|---|
| Revision | `5e7b2b1b` statt neuester | alle Messungen darauf; `aa8c91ca` ohne multilingual |
| GPU | verschoben | CPU 304 ms p50 reicht; GPU verlangt eigene Äquivalenzstudie |
| Checkpoint-Wechsel (19–50 s) | weder längere Frist noch `max_loaded=2` | Client und ADVISE brechen nach 5 s ab → ABSTAIN |
| `mem_limit` | 3g | Wechsel läuft unter 3g ohne OOM; 4g + voller jev-Container > VM |
| Keystone-DB | nicht zurückgespielt | Rückspielen löscht auch Fremdänderungen, nicht umkehrbar |
| Browse-Agent-Teil von Phase 4 | nicht ausgeführt | jev pausiert; 78 % Navigationsfehler würden die Messung verfälschen |
| Terraform | nicht eingesetzt | nur lokale Compose-Infrastruktur |

## 6. Tests

<!-- TESTS -->

## 7. Negative Evidenz

- Der Hersteller veröffentlicht keine Guard-Metrik und keine Sicherheits-Trainingsdaten.
- Kein in-session Probensatz trennt einen Recall von 0,55 von 0,95.
- Vergleichbare Guards fallen adaptiven Angriffen in über 90 % der Fälle.
- Als harmlose Bitte formulierte Anweisungen sind die dokumentierte Lücke von Guard-Klassifikatoren.
- Das LM-Studio-Modell (Recall 0,286) ist ein anderes Modell und sagt nichts über Laya.

## 8. Offen

Genau ein Folgeauftrag: `05-WORK-ORDERS/NEXT-SESSION-LOGOS1-LAYA-JUROR-INTEGRATION-R1.md`.
