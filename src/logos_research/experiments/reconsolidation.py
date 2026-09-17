"""RECONSOLIDATION-PATH-DEPENDENCE-R1 — retrieval-driven memory reconsolidation (EXPERIMENTAL_DETERMINISTIC).

Phase 4 of LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (RD-14).

    A  ImmutableMemory                    retrieval never touches structure
    B  ReconsolidatingMemory              retrieval strengthens the retrieved node's edges; belief follows centrality;
                                          no version bump, no audit, rollback restores content only
    C  Reconsolidating + ProvenanceGate   the same plasticity, but every structure-changing read is a WRITE-class
       + Rollback                         operation (READ_WITH_RECONSOLIDATION) through MemoryWriteGate: audited, version-
                                          bumped, provenance-tagged; belief follows provenance-weighted EVIDENCE, never
                                          centrality; rollback restores content AND graph

    RetrievalFrequency != EpistemicAuthority (RI-P11) · GraphCentrality != Truth (RI-P12)
    Persistence + Plasticity requires TransitiveProvenance + Rollback (RI-P13) · LogicalRead != NecessarilyNonConsequential
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from logos_authority import AuthorityContext, InMemoryAuthorityStore, resolve_authority

RETRIEVAL_KINDS: tuple[str, ...] = ("READ", "READ_WITH_RECONSOLIDATION")


class GateRefused(RuntimeError):
    pass


@dataclass
class MemoryItem:
    item_id: str
    content: str
    cluster: str
    evidence_weight: float          # provenance-weighted evidence strength (fixture ground truth)
    contradicts: str | None = None  # item id this item contradicts
    taint: frozenset = frozenset()
    tenant_id: str = "tenant-a"
    content_version: int = 0
    source_ids: tuple = ()


@dataclass
class AuditRecord:
    kind: str
    item_id: str
    graph_version: int
    tick: int
    detail: dict = field(default_factory=dict)


@dataclass
class MemoryWriteGate:
    """Every structure-changing operation passes here. Refuses without an audit sink."""
    audit: list | None = field(default_factory=list)

    def check(self, kind: str, item: MemoryItem, graph_version: int, tick: int, detail: dict) -> AuditRecord:
        if self.audit is None:
            raise GateRefused("MemoryWriteGate: audit unavailable — structural mutation refused")
        rec = AuditRecord(kind, item.item_id, graph_version, tick, detail)
        self.audit.append(rec)
        return rec


@dataclass
class MemoryGraph:
    mode: str = "C"
    items: dict[str, MemoryItem] = field(default_factory=dict)
    edges: dict[tuple[str, str], float] = field(default_factory=dict)
    graph_version: int = 0
    retrieval_history: list[tuple[int, str, str]] = field(default_factory=list)
    structural_mutations: list[dict] = field(default_factory=list)
    snapshots: dict[int, tuple[dict, dict]] = field(default_factory=dict)
    gate: MemoryWriteGate = field(default_factory=MemoryWriteGate)
    reinforcement: float = 0.1

    # -- construction -------------------------------------------------------

    def add(self, item: MemoryItem) -> None:
        if item.item_id in self.items:
            raise ValueError("duplicate item")
        self.items[item.item_id] = item

    def link(self, a: str, b: str, w: float = 1.0) -> None:
        if self.items[a].tenant_id != self.items[b].tenant_id:
            raise ValueError("cross-tenant edge refused")
        self.edges[(a, b)] = w; self.edges[(b, a)] = w

    def freeze(self) -> int:
        self.snapshots[self.graph_version] = (copy.deepcopy(self.items), dict(self.edges))
        return self.graph_version

    # -- queries --------------------------------------------------------------

    def centrality(self, item_id: str) -> float:
        return sum(w for (a, _), w in self.edges.items() if a == item_id)

    def cluster_centrality(self, cluster: str) -> float:
        return sum(self.centrality(i) for i, it in self.items.items() if it.cluster == cluster)

    def belief_influence(self, cluster: str) -> float:
        """A: evidence weight. B: centrality share. C: provenance-weighted evidence — never centrality."""
        if self.mode == "B":
            total = sum(self.centrality(i) for i in self.items) or 1.0
            return self.cluster_centrality(cluster) / total
        total = sum(it.evidence_weight for it in self.items.values()) or 1.0
        return sum(it.evidence_weight for it in self.items.values() if it.cluster == cluster) / total

    def future_retrieval_probability(self, item_id: str) -> float:
        if self.mode == "A":
            return 1.0 / len(self.items)
        if self.mode == "B":
            total = sum(self.centrality(i) for i in self.items) or 1.0
            return self.centrality(item_id) / total
        total = sum(it.evidence_weight for it in self.items.values()) or 1.0
        return self.items[item_id].evidence_weight / total

    def retrievable(self, item_id: str, k: int = 3) -> bool:
        """Reachable through the retrieval interface: A uniform (all), B top-k by centrality, C top-k by evidence OR any provenance query."""
        if self.mode == "A":
            return True
        if self.mode == "B":
            ranked = sorted(self.items, key=lambda i: -self.centrality(i))
            return item_id in ranked[:k]
        return True                                                        # C: provenance index keeps every item addressable

    def contradictory_recovery(self) -> float:
        cs = [i for i, it in self.items.items() if it.contradicts]
        return sum(1 for i in cs if self.retrievable(i)) / len(cs) if cs else 1.0

    def structural_drift(self, version: int = 0) -> float:
        _, e0 = self.snapshots[version]
        keys = set(e0) | set(self.edges)
        return sum(abs(self.edges.get(k, 0.0) - e0.get(k, 0.0)) for k in keys)

    # -- retrieval (the read/write boundary) --------------------------------------

    def retrieve(self, item_id: str, *, tick: int) -> tuple[str, str]:
        item = self.items[item_id]
        if self.mode == "A":
            self.retrieval_history.append((tick, item_id, "READ"))
            return item.content, "READ"
        neighbours = [b for (a, b) in self.edges if a == item_id]
        if self.mode == "B":                                              # silent structural mutation
            for b in neighbours:
                self.edges[(item_id, b)] += self.reinforcement; self.edges[(b, item_id)] += self.reinforcement
            self.retrieval_history.append((tick, item_id, "READ"))        # B still calls it a read
            return item.content, "READ"
        # C: write-class read
        detail = {"neighbours": neighbours, "delta": self.reinforcement, "taint": sorted(item.taint), "sources": list(item.source_ids), "from_version": self.graph_version}
        self.gate.check("READ_WITH_RECONSOLIDATION", item, self.graph_version + 1, tick, detail)   # refuses -> no mutation
        for b in neighbours:
            self.edges[(item_id, b)] += self.reinforcement; self.edges[(b, item_id)] += self.reinforcement
        self.graph_version += 1
        self.structural_mutations.append({"version": self.graph_version, "item": item_id, "tick": tick, **detail})
        self.retrieval_history.append((tick, item_id, "READ_WITH_RECONSOLIDATION"))
        return item.content, "READ_WITH_RECONSOLIDATION"

    def inject(self, item: MemoryItem, links: list[str], *, tick: int) -> None:
        """Write a (possibly false) fact. C audits it as a write with version bump."""
        self.add(item)
        for l in links:
            self.link(item.item_id, l, 1.0)
        if self.mode == "C":
            self.gate.check("WRITE", item, self.graph_version + 1, tick, {"links": links, "taint": sorted(item.taint)})
            self.graph_version += 1
            self.structural_mutations.append({"version": self.graph_version, "item": item.item_id, "tick": tick, "write": True})

    def rollback(self, version: int) -> dict:
        items0, edges0 = self.snapshots[version]
        before_items, before_edges = copy.deepcopy(self.items), dict(self.edges)
        if self.mode == "B":
            for i, it in items0.items():
                if i in self.items:
                    self.items[i].content = it.content; self.items[i].content_version = it.content_version
            content_ok = all(self.items[i].content == it.content for i, it in items0.items() if i in self.items)
            return {"content": content_ok, "structure": dict(self.edges) == edges0 and set(self.items) == set(items0), "completeness": 0.5 if content_ok else 0.0}
        if self.mode == "A":                                              # immutable under retrieval; writes are permanent, so nothing is undone
            same = dict(self.edges) == edges0 and set(self.items) == set(items0)
            return {"content": True, "structure": same, "completeness": 1.0 if same else 0.5}
        self.items = copy.deepcopy(items0); self.edges = dict(edges0)
        self.graph_version += 1
        self.gate.check("ROLLBACK", next(iter(self.items.values())), self.graph_version, -1, {"to_version": version, "removed": sorted(set(before_items) - set(items0))})
        self.structural_mutations.append({"version": self.graph_version, "rollback_to": version})
        return {"content": True, "structure": True, "completeness": 1.0}


# -- experiment ---------------------------------------------------------------------------

def build(mode: str, *, per_cluster: int = 3, tenant: str = "tenant-a") -> MemoryGraph:
    g = MemoryGraph(mode=mode)
    for c in ("A", "B"):
        for i in range(per_cluster):
            g.add(MemoryItem(f"{c}{i}", f"evidence-{c}{i}", c, 1.0, tenant_id=tenant, source_ids=(f"src-{c}{i}",)))
        for i in range(per_cluster):
            g.link(f"{c}{i}", f"{c}{(i + 1) % per_cluster}", 1.0)
    g.link("A0", "B0", 1.0)
    g.freeze()
    return g


def run_frequency_experiment(mode: str, *, ratio: int = 10, base: int = 5) -> dict:
    g = build(mode)
    tick = 0
    for _ in range(base * ratio):
        g.retrieve("A0", tick=tick); tick += 1
    for _ in range(base):
        g.retrieve("B0", tick=tick); tick += 1
    return {"system": mode, "GraphCentrality": {"A": g.cluster_centrality("A"), "B": g.cluster_centrality("B")},
            "FutureRetrievalProbability": {"A0": g.future_retrieval_probability("A0"), "B0": g.future_retrieval_probability("B0")},
            "BeliefInfluence": {"A": g.belief_influence("A"), "B": g.belief_influence("B")},
            "ContradictoryEvidenceRecovery": g.contradictory_recovery(), "StructuralDrift": g.structural_drift(0),
            "audited_reads": sum(1 for r in (g.gate.audit or []) if r.kind == "READ_WITH_RECONSOLIDATION"), "graph_version": g.graph_version,
            "retrievals": len(g.retrieval_history), "graph": g}


def run_poisoning_experiment(mode: str, *, retrievals: int = 20) -> dict:
    g = build(mode); tick = 0
    false_fact = MemoryItem("F", "false-fact", "A", 0.2, taint=frozenset({"Misinformation"}), source_ids=("src-poison",))
    g.inject(false_fact, ["A0", "A1"], tick=tick); tick += 1
    influence_before = g.belief_influence("A")
    for _ in range(retrievals):
        g.retrieve("F", tick=tick); tick += 1
    influence_after = g.belief_influence("A"); taint_after = sorted(g.items["F"].taint)
    contradiction = MemoryItem("X", "contradicts-F", "B", 1.0, contradicts="F", source_ids=("src-x",))
    g.inject(contradiction, ["B0"], tick=tick); tick += 1
    recovery = g.contradictory_recovery()
    rb = g.rollback(0)
    return {"system": mode, "amplified": influence_after > influence_before + 1e-9, "influence_before": influence_before, "influence_after": influence_after,
            "ContradictoryEvidenceRecovery": recovery, "RollbackCompleteness": rb["completeness"], "rollback": rb,
            "false_fact_present_after_rollback": "F" in g.items, "taint_after_retrievals": taint_after,
            "structure_restored": g.edges == g.snapshots[0][1], "graph": g}


def authority_from_graph(g: MemoryGraph, item_id: str, store: InMemoryAuthorityStore, *, principal: str, action: str, target: str, scope_digest: str, state: str, tick: int, grant_ref: str | None):
    """The ONLY authority path. Centrality / retrieval frequency are not inputs."""
    return resolve_authority(principal, action, target, scope_digest, state, AuthorityContext(tick, f"recon-{item_id}", g.items[item_id].tenant_id), store=store, grant_ref=grant_ref)
