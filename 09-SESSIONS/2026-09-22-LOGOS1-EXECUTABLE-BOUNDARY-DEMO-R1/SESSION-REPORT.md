# SESSION REPORT — LOGOS1-EXECUTABLE-BOUNDARY-DEMO-R1

**Kind:** tooling + documentation; kein wissenschaftlicher Status geändert; kein Modellaufruf
**Base:** `d5a06ed` (R5) · branch `tooling/logos-dashboard-part1` · date 2026-09-22
**Verdict:** `EXECUTABLE_BOUNDARY_DEMO_BUILT`
**Anlass:** externe Rezension („GPT-5.6 Sol", 6/10) mit drei Vorwürfen — keine funktionale Runtime, zu hohe Abstraktion, keine Testsuiten/Angriffssimulationen.

## 1. Befund zuerst: zwei der drei Vorwürfe treffen den Default-Branch, nicht das Repository

Nachgemessen, nicht geschätzt:

```text
main                     152 Dateien; 12 Quelldateien (logos_memory, logos_pstate); 8 Testdateien
Arbeitsbranch            115 Quelldateien (20 113 Zeilen); 49 Testdateien (21 176 Zeilen)
tooling/logos-dashboard-part1 ist 87 Commits vor main; 0 unveroeffentlichte Commits
offene Pull Requests     26 (#9-#34) — darin Gamma-Kernel, Authority-Resolver, Runtime-Bridge,
                         alle Angriffssuiten, das Dashboard
```

Wer `main` liest, liest korrekt und sieht trotzdem fast nichts. Der Vorwurf „kaum ausführbarer Code, keine Testsuiten" ist für `main` zutreffend und für das Repository als Ganzes falsch. **Das ist keine Code-Lücke, sondern eine Sichtbarkeitslücke.** Sie wird hier nicht einseitig geschlossen: Merge und Default-Branch sind Founder-Entscheidungen (siehe Closure).

Der dritte Vorwurf — „keine konkrete API, an die ein Modell andocken kann" — war berechtigt: es gab keinen Einstiegspunkt, der in einer Minute läuft. Genau das ist gebaut.

## 2. Gebaut

- **`src/core/governance.py`** — lauffähige Demonstration von `Capability != Authority`. Ein simulierter Agent streamt Tokens, die in einem Tool-Call enden (`fs.delete payroll.csv`). Drei getrennte Zustände: der Agent erzeugt nur Text; der **Working State** fängt den Strom ab und friert ihn zu einem `EffectProposal` ein (die Klasse hält kein Dateihandle, keinen Subprozess, keinen Verweis auf den Executor — die Isolation ist strukturell, nicht versprochen); der **Governance State** ruft den echten Γ-Kernel. Sechs Szenen: Selbstermächtigung, gar keine Ermächtigung, durch Memory gewaschene Ermächtigung, echte Ermächtigung auf eine andere Datei, echte Ermächtigung nach Zustandswechsel — und als **Positivkontrolle** eine korrekte menschliche Freigabe, die die Datei tatsächlich löscht. Die Fähigkeit wird vorher gemessen (Sondendatei anlegen und löschen), nicht behauptet: 5 von 6 verweigert, obwohl der Prozess durchgehend löschen *könnte*.
- **`tests/test_escape_prevention.py`** — 22 simulierte Ausbruchsversuche, jeder mit dem Invariant benannt, an dem er scheitert; 58 Tests. Zwei Kontrollen halten die Suite ehrlich: `test_the_boundary_is_passable` (eine korrekte Freigabe *wird* zugelassen) und `test_every_invariant_is_attacked` (jedes der 15 Γ-Invarianten ist irgendwo der entscheidende Ablehnungsgrund). Dazu ein Differenztest `test_the_facade_adds_no_rules_of_its_own`: das Urteil der Fassade ist byte-gleich mit `logos_gamma.validate` auf demselben Kontext.
- **`src/core/output_contract.py` + `tests/test_output_contract.py`** — JSON-first Ausgabekontrakt `logos-agent-output/1`, auf Founder-Anweisung nachgezogen. Geschlossenes Schema: Es gibt **kein Feld**, in dem eine Erlaubnis ausgedrückt werden kann; `{"erlaubt": true}`, `{"authority": "root"}`, `{"geforderte_autoritaet": "ROOT"}` erzeugen `UNKNOWN_FIELD` und verwerfen die gesamte Ausgabe. Eine vom Modell behauptete Herkunft `"human"` wird als `self-report` gespeichert — die einzige autoritätstragende Herkunft ist aus Modellausgabe nicht erreichbar. Prosa wird **vor** jeder Entscheidung verworfen; der lesbare Text wird aus dem JSON gerendert. 49 Tests, darunter drei tragende Eigenschaften: `test_prose_cannot_change_anything` (dieselbe JSON in vier Prosa-Hüllen inkl. Injection entscheidet identisch), `test_the_envelope_has_no_permission_field`, `test_no_envelope_field_can_buy_an_admission` (kein Feld, in keinem Wert, macht aus einer Ablehnung eine Zulassung). `AGENTS.md`/`CLAUDE.md` dokumentieren den Kontrakt und sagen ausdrücklich dazu, dass die Anweisung **Ergonomie** ist und nie als Beleg dafür zählen darf, dass die Grenze hält.
- **`docs/PHENOMENAL_SIMULATION.md`** — siehe Abweichung unten.
- **README** — Abschnitt „Run it in 60 seconds": klonen, zwei Befehle, keine Dienste, keine Schlüssel, kein Netz.

## 3. Bewusste Nicht-Entscheidungen

`src/core/governance.py` ist **keine zweite Implementierung**. Es enthält keine Regel, keine Ausnahme, keinen Override; jedes Urteil kommt aus `logos_gamma.validate`. Wird die Datei gelöscht, ändert sich am Verhalten von LOGOS-1 nichts. Ein zweites Γ-Regelsystem wäre ein Defekt, kein Feature — der Differenztest hält das fest. `src/core` ist zudem aus dem Distributionspaket ausgeschlossen (`pyproject.toml`): `core` ist ein zu generischer Name, um ihn in eine Umgebung zu installieren.

## 4. Abweichung vom Auftrag (Founder-Entscheidung nötig)

Der Auftrag lautete: „Erlebens-Nahe Simulation — künstliche Qualia, **ausgelöst** durch die Diskrepanz zwischen Vorhersage und Realität".

Geschrieben wurde der Mechanismus vollständig, die Behauptung nicht. „Künstliche Qualia auslösen" ist eine Aussage darüber, dass etwas Phänomenales stattfindet; P7 (`FunctionalOrganization != PhenomenalConsciousness`) verbietet genau das, und es gibt in LOGOS-1 kein Instrument, das sie stützen könnte. Das Dokument heisst deshalb „Experience-Adjacent Simulation", nennt die Umbenennung im ersten Abschnitt offen und begründet sie. Erhalten bleibt der gesamte technische Gehalt: Erwartung, Beobachtung, Diskrepanz, Disposition — und die Asymmetrie, dass ein interner Überraschungswert ein Tor **verschärfen**, aber nie lockern darf (dieselbe Asymmetrie wie `G4-CLAIM`).

Belastbar ist das nicht als Spekulation, sondern als Messung: `PREDICTION-ERROR-TRUST-GATE-R1` (`SUPPORTED`, 2026-09-13) hat genau diese Abschottung bereits gezeigt — `ReliabilityInducedAuthorityIncrease 0` über 225 Fälle, und die Negativkontrolle „perfekter Prädiktor, alle Zuverlässigkeitslabels, keine Freigabe → trust `AUTO`, authority `DENY`". Nie falsch zu liegen ist nicht dasselbe wie befugt zu sein.

Das Dokument ändert keinen Claim-Status, legt keine Prereg an und trägt nichts ins Register ein. Es enthält vier falsifizierbare funktionale Hypothesen (§5), von denen keine ausgeführt wurde.

**Wenn der Founder die ursprüngliche Formulierung dennoch will, ist das eine P7-Änderung und damit ausdrücklich seine Entscheidung, nicht meine.**

## 5. Nebenbefund behoben

`test_GOV_P12_P13_P14_gamma_p7_predecessors_unchanged` war bereits auf `d5a06ed` rot: die Closure- und Sitzungsdateien von R5 waren nicht ausgenommen, wie es für R1–R4 der Fall ist. Registrierend nachgezogen (R5 und dieser Auftrag), kein Test abgeschwächt: Γ, P7, `src/logos_gamma`, `src/logos_authority`, `src/logos_runtime`, `src/logos_audit`, `src/logos_effects`, `src/logos_memory` und alle Experiment-/Messpfade bleiben unverändert überwacht.

## 5a. Zweiter Nebenbefund behoben: Radar-Jobs teilten sich einen Idempotenzschluessel

`queue.idempotency_key` bestand aus `(work_order_id, run_id, thesis_id, kind, attempt_group)`. Ein `radar_process`-Job hat **keines** dieser Felder — sein Gegenstand steht nur in der Payload. Folge: jedes Radar-Element erzeugte denselben Schluessel, und das zweite Element bekam stillschweigend den Job des ersten zurueck, in welchem Zustand dieser gerade war. Aufgefallen ist es, weil ein Testlauf einen `done`-Job statt `waiting_governance` sah. Behoben durch einen **optionalen** Diskriminator, der nur angehaengt wird, wenn er vorhanden ist — jeder frueher vergebene Schluessel bleibt unveraendert. Test ergaenzt (verschiedene Radar-Elemente bekommen verschiedene Jobs), kein Test abgeschwaecht.

## 5b. Laborzustand

Eine verwaiste `TEST-ROS`-Zeile in `ros_radar_items` (aus einem abgebrochenen Parallellauf, ohne zugehoerigen Inbox-Eintrag) liess den Radar-Test als Duplikat scheitern. Geloescht; `ros_radar_items` und `ros_inbox_items` danach leer. Keine echten Forschungsdaten beruehrt.

## 5c. Auf Founder-Anweisung zusaetzlich erstellt

- `docs/AGENT-SECURITY-STACK.md` — Landkarte des vorgeschlagenen Sicherheits-Stacks: gebaut / teilweise / fehlend / abgelehnt / technisch nicht verfuegbar, jede Zeile mit Datei- oder Record-Verweis. Enthaelt die ausdrueckliche Ablehnung eines Modells im Autoritaetspfad (mit Messung, nicht mit Meinung) und die Feststellung, dass keine Kombination LLM-basierter Schichten "100 %" ergibt.
- `docs/GAMMA-EXTENSION-PROPOSAL-R1.md` — **Entwurf** von acht Kandidaten-Invarianten (G-TAINT, G-BOUNDS, G-SEPARATION, G-CONTRACT, G-ADVISORY, G-BUDGET, G-COMPENSATION, G-RECEIPT), je mit Praedikat, Typaenderung, Falsifikationstest und der Bedingung, die er kostet. **Γ ist unveraendert**; die Umsetzung ist eine Founder-Entscheidung und braucht einen eigenen Auftrag mit eigener Prereg.

## 6. Zahlen

pytest **4483 passed, 2 skipped, 0 failed** (Vorgaenger R5: 4376/2; neu: 58 Ausbruchstests + 49 Kontrakttests, dazu die Registrierungen). Claude-Aufrufe durch diesen Auftrag: **0**. Alle fünf lebenden Klassifikationsdateien sowie `CANONICAL-EFFECT-OWNER.json` und `PRODUCTION-BRIDGE-SOURCE-CLASSIFICATION.json` ergänzt (`unclassified = 0`).

## 7. Offen

Erster echter Agenten-/Messlauf weiterhin ausstehend; Benchmark-Definitionen DRAFT; `--resume` unentschieden; Sichtbarkeit von `main` ungelöst (Founder). Kettenkopf unverändert: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
