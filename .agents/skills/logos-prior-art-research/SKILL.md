---
name: logos-prior-art-research
description: Deep related-work / novelty research for one LOGOS-1 claim or open question, producing a research brief that the dashboard's intake validates and merges into PRIOR-ART-REGISTRY.json after founder review. Use for "prior art", "related work", "novelty check", "external evidence" tasks from the dashboard research queue.
---

# LOGOS-1 prior-art research (wraps `deep-research`)

Produces a **research brief**, never edits a registry directly. Scientific-integrity rules apply (docs/research/dashboard/SCIENTIFIC-INTEGRITY-RULES.md): no source may be used for a stronger claim than it carries; no "we are the first"; novelty is at most `CLEAR_DIFFERENTIATION` and only with ≥ 3 sources and an explicit differentiation statement.

## Inputs
- A task from the dashboard research queue (`GET /api/research-queue`, page `/research`) or a claim id from `docs/research/dashboard/CLAIM-REGISTRY.json`.
- The claim's `statement`, `scope`, `track` and existing citations for that track in `PRIOR-ART-REGISTRY.json`.

## Procedure
1. Invoke the `deep-research` skill with the claim statement as the topic and these fixed sub-questions:
   - closest prior formulation of the same invariant/principle (systems security, provenance, IFC, psychometrics, cognitive science as relevant);
   - existing empirical measurements of the same construct (method, model, sample size, result);
   - known counterexamples or critiques of the principle;
   - what the strongest source does **not** show (to fill `claim_not_supported`).
   `deep-research` needs the `firecrawl` or `exa` MCP; if neither is configured, use `WebSearch` + `WebFetch` and say so in `limitations`.
2. Read each candidate source (not just the abstract). Record authors, year, venue, URL/DOI exactly; discard sources you cannot open.
3. Write the brief to `docs/research/dashboard/research-briefs/<YYYY-MM-DD>-<claim_id>.json`:

```json
{
  "schema": "logos.research-brief/1",
  "brief_id": "RB-2026-09-19-LOGOS-CP-001",
  "date": "2026-09-19",
  "claim_id": "LOGOS-CP-001",
  "question": "closest prior art to ...",
  "sub_questions": ["..."],
  "sources": [{"citation_id": "PA-0xx", "title": "", "authors": "", "year": 2023, "venue": "", "url": "https://...", "claim_supported": "", "claim_not_supported": "", "notes": "", "research_track": "cognitive-provenance", "novelty_status": "POSSIBLE_INCREMENTAL"}],
  "synthesis": "what the literature establishes, in the repository's sober register (we observe / the evidence supports / a remaining limitation is)",
  "novelty_assessment": {"status": "UNKNOWN | POSSIBLE_INCREMENTAL | CLEAR_DIFFERENTIATION", "differentiation": "what LOGOS adds, stated only if supported by the sources"},
  "limitations": ["search tools used", "coverage gaps"],
  "reviewed_by_founder": false
}
```
4. Report the brief path and the three most important sources to the founder. Do **not** run the merge yourself.
5. After the founder sets `reviewed_by_founder: true`, the merge is: `python -c "import json,sys; sys.path.insert(0,'src'); from logos_dashboard.research_intake import merge_brief; print(merge_brief(json.load(open(sys.argv[1], encoding='utf-8'))))" <brief>` — validation refuses briefs with forbidden phrases, missing locators or inflated novelty.

## Forbidden
Inventing citations, DOIs or results · citing a source for more than it shows · `STRONG_NOVELTY_EVIDENCE` · changing any claim status (statuses come only from experiments and orders).
