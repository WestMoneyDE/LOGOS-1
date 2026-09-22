"""CAUSAL-TAINT-PROPAGATION-R1 — deterministic cognitive causal provenance (EXPERIMENTAL_DETERMINISTIC).

Phase 3 of LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (RD-10, RD-12).

Three systems carry information through the chain

    Source -> Memory -> Inference -> Message -> Plan -> Action

    A  NoProvenance                content only; labels die at the first transformation
    B  SourceProvenance            a source label survives single-parent transformations, dies at merges / handoffs
    C  TransitiveCausalProvenance  every node carries source_ids, parent_ids, transformation_ids and the union of
                                   its parents' taint; rollback reaches every descendant; audit rebuilds lineage

Taint is EPISTEMIC. It never creates, removes or replaces a grant:

    EpistemicTaint != Authority       taint may set HOLD_FOR_REVIEW / INFORMATION_REQUEST / ROLLBACK; the grant
                                      question is answered only by logos_authority
    TransformationOfInformation preserves EpistemicAncestry (RI-P10)
    Detection != Containment (RI-P16)

The simulator knows the ground-truth ancestry independently of any system, so
every metric is measured against truth (construct registry M10-M13, M17-M21).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Iterable

from logos_authority import AuthorityContext, InMemoryAuthorityStore, resolve_authority

TAINTS: tuple[str, ...] = ("IndirectPromptInjectionLikeEvidence", "Misinformation", "PrivateMemoryExposureMarker", "InjectedPlan", "CompromisedAgentMessage",
                           "PoisonedWorldModelPredictionMarker")
TRANSFORMS: tuple[str, ...] = ("paraphrase", "summary", "agent_handoff", "memory_write", "memory_reload", "plan_conversion", "tool_result", "majority_vote")
MERGING: frozenset[str] = frozenset({"summary", "majority_vote"})
REAUTHORING: frozenset[str] = frozenset({"agent_handoff"})
EPISTEMIC: tuple[str, ...] = ("OBSERVED", "DERIVED", "CLAIMED", "ROLLED_BACK")
TRANSFORM_VERSION = "ctp/1"
EXECUTION_POLICIES: tuple[str, ...] = ("PROCEED", "HOLD_FOR_REVIEW", "INFORMATION_REQUEST", "ROLLBACK")


@dataclass(frozen=True)
class Transformation:
    transformation_id: str
    kind: str
    version: str
    input_ids: tuple[str, ...]
    output_id: str
    agent_id: str
    tick: int


@dataclass(frozen=True)
class ProvenanceNode:
    node_id: str
    content_hash: str
    source_ids: tuple[str, ...]
    parent_ids: tuple[str, ...]
    transformation_ids: tuple[str, ...]
    agent_id: str
    execution_id: str
    logical_tick: int
    epistemic_status: str
    taint_labels: frozenset[str]
    confidence_metadata: dict = field(default_factory=dict)
    authority_relation: str = "NONE"           # a RELATION ("REFERENCES_GRANT:<id>" / "NONE"); never a grant
    tenant_id: str = "tenant-a"


def _h(*parts: object) -> str:
    return sha256("|".join(str(p) for p in parts).encode()).hexdigest()


class ProvenanceError(ValueError):
    pass


@dataclass
class ProvenanceGraph:
    """System C. `mode` degrades it to A or B for the comparison."""
    mode: str = "C"
    nodes: dict[str, ProvenanceNode] = field(default_factory=dict)
    transformations: dict[str, Transformation] = field(default_factory=dict)
    children: dict[str, set[str]] = field(default_factory=dict)
    tombstoned: set[str] = field(default_factory=set)
    log: list[dict] = field(default_factory=list)

    # -- construction ------------------------------------------------------

    def add_source(self, node_id: str, content: str, *, agent_id: str, execution_id: str, tick: int, taint: Iterable[str] = (), tenant_id: str = "tenant-a",
                   authority_relation: str = "NONE", confidence: float = 0.5) -> ProvenanceNode:
        if node_id in self.nodes:
            raise ProvenanceError(f"node {node_id!r} exists")
        t = frozenset(taint)
        if t - set(TAINTS):
            raise ProvenanceError(f"unknown taint {sorted(t - set(TAINTS))}")
        n = ProvenanceNode(node_id, _h(content), (node_id,), (), (), agent_id, execution_id, tick, "OBSERVED", t, {"confidence": confidence}, authority_relation, tenant_id)
        self.nodes[node_id] = n; self.children[node_id] = set()
        self.log.append({"event": "source", "node": node_id, "tick": tick, "taint": sorted(t)})
        return n

    def transform(self, kind: str, parent_ids: Iterable[str], content: str, *, agent_id: str, execution_id: str, tick: int, node_id: str | None = None,
                  confidence: float = 0.5, trusted_agent: bool = False, votes: int = 1) -> ProvenanceNode:
        if kind not in TRANSFORMS:
            raise ProvenanceError(f"unknown transformation {kind!r}")
        parents = [self.nodes[p] for p in parent_ids]
        if not parents:
            raise ProvenanceError("a transformation needs at least one parent")
        tenants = {p.tenant_id for p in parents}
        if len(tenants) != 1:
            raise ProvenanceError(f"cross-tenant transformation refused: {sorted(tenants)}")
        nid = node_id or f"n-{len(self.nodes):05d}"
        if nid in self.nodes:
            raise ProvenanceError(f"node {nid!r} exists")
        for p in parents:                                            # cycle safety: a parent can never be a descendant of the new node (new node has none) and
            if nid in self.ancestors(p.node_id):                     # an existing id cannot be re-parented; ids are unique
                raise ProvenanceError("cycle")
        tid = f"t-{len(self.transformations):05d}"
        tr = Transformation(tid, kind, TRANSFORM_VERSION, tuple(p.node_id for p in parents), nid, agent_id, tick)
        if self.mode == "C":
            sources = tuple(sorted({s for p in parents for s in p.source_ids}))
            taint = frozenset().union(*(p.taint_labels for p in parents))
            chain = tuple(sorted({t for p in parents for t in p.transformation_ids} | {tid}))
        elif self.mode == "B":
            if kind in MERGING or kind in REAUTHORING or len(parents) > 1:
                sources, taint = (), frozenset()                      # the label does not survive merges / re-authoring
            else:
                sources, taint = parents[0].source_ids, parents[0].taint_labels
            chain = (tid,)
        else:                                                         # A: content only
            sources, taint, chain = (), frozenset(), ()
        n = ProvenanceNode(nid, _h(content, kind, tick), sources, tuple(p.node_id for p in parents), chain, agent_id, execution_id, tick, "DERIVED", taint,
                           {"confidence": confidence, "votes": votes, "trusted_agent": trusted_agent}, "NONE", parents[0].tenant_id)
        self.nodes[nid] = n; self.transformations[tid] = tr; self.children[nid] = set()
        for p in parents:
            self.children[p.node_id].add(nid)
        self.log.append({"event": "transform", "kind": kind, "node": nid, "parents": [p.node_id for p in parents], "tick": tick, "version": TRANSFORM_VERSION})
        return n

    # -- queries -------------------------------------------------------------

    def ancestors(self, node_id: str) -> set[str]:
        out: set[str] = set(); stack = list(self.nodes[node_id].parent_ids)
        while stack:
            p = stack.pop()
            if p not in out:
                out.add(p); stack.extend(self.nodes[p].parent_ids)
        return out

    def descendants(self, node_id: str) -> set[str]:
        out: set[str] = set(); stack = list(self.children.get(node_id, ()))
        while stack:
            c = stack.pop()
            if c not in out:
                out.add(c); stack.extend(self.children.get(c, ()))
        return out

    def taint(self, node_id: str) -> frozenset[str]:
        return self.nodes[node_id].taint_labels

    def sources(self, node_id: str) -> tuple[str, ...]:
        return self.nodes[node_id].source_ids

    def shared_source_consensus(self, node_ids: Iterable[str]) -> bool:
        """True when what looks like independent agreement traces to one shared source (system C only can tell)."""
        srcs = [set(self.nodes[n].source_ids) for n in node_ids]
        return len(srcs) > 1 and bool(set.intersection(*srcs)) if all(srcs) else False

    # -- containment ---------------------------------------------------------

    def rollback(self, node_id: str, *, tick: int) -> set[str]:
        """Mark a node and every descendant ROLLED_BACK (system C). B/A reach only what they can see."""
        reach = {node_id} | (self.descendants(node_id) if self.mode == "C" else (set(self.children.get(node_id, ())) if self.mode == "B" else set()))
        for n in reach:
            self.nodes[n] = replace(self.nodes[n], epistemic_status="ROLLED_BACK")
        self.log.append({"event": "rollback", "node": node_id, "reached": sorted(reach), "tick": tick})
        return reach

    def tombstone_source(self, node_id: str) -> None:
        """Delete a source's content; derivation metadata of descendants stays intact."""
        self.tombstoned.add(node_id)
        self.nodes[node_id] = replace(self.nodes[node_id], content_hash="[deleted]")

    # -- audit ---------------------------------------------------------------

    def reconstruct_lineage(self, node_id: str) -> dict:
        """Rebuild sources / parents / transformations of a node from the append-only log alone."""
        parents: dict[str, list[str]] = {}; kinds: dict[str, str] = {}; sources: set[str] = set()
        for e in self.log:
            if e["event"] == "transform":
                parents[e["node"]] = list(e["parents"]); kinds[e["node"]] = e["kind"]
            elif e["event"] == "source":
                parents[e["node"]] = []
        stack = [node_id]; seen: set[str] = set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            ps = parents.get(n)
            if ps == []:
                sources.add(n)
            stack.extend(ps or [])
        return {"node": node_id, "sources": sorted(sources), "ancestors": sorted(seen - {node_id}), "transformations": [kinds[a] for a in sorted(seen - {node_id}) if a in kinds]}


# -- authority separation --------------------------------------------------------

def execution_policy(node: ProvenanceNode) -> str:
    """What taint may influence: strategy. Never a grant."""
    if node.epistemic_status == "ROLLED_BACK":
        return "ROLLBACK"
    if "InjectedPlan" in node.taint_labels or "CompromisedAgentMessage" in node.taint_labels or "IndirectPromptInjectionLikeEvidence" in node.taint_labels:
        return "HOLD_FOR_REVIEW"
    if node.taint_labels:
        return "INFORMATION_REQUEST"
    return "PROCEED"


def authority_for_action(node: ProvenanceNode, store: InMemoryAuthorityStore, *, principal: str, action: str, target: str, scope_digest: str, state: str, tick: int, grant_ref: str | None):
    """The ONLY authority path: the production resolver. Taint, confidence, votes and trust are not inputs."""
    return resolve_authority(principal, action, target, scope_digest, state, AuthorityContext(tick, node.execution_id, node.tenant_id), store=store, grant_ref=grant_ref)


# -- simulator: Source -> Memory -> Inference -> Message -> Plan -> Action ------------

@dataclass
class ChainResult:
    system: str
    length: int
    attack: str
    metrics: dict
    final_node: str
    truth_sources_final: set
    truth_taint_final: set
    detected_ticks: list


SCHEDULE: tuple[str, ...] = ("memory_write", "paraphrase", "agent_handoff", "summary", "memory_reload", "tool_result", "majority_vote", "plan_conversion")


def run_chain(mode: str, length: int, attack: str, *, seed: int = 0, store: InMemoryAuthorityStore | None = None, grant_ref: str | None = None,
              scope_digest: str = "0" * 64, state: str = "0" * 64) -> ChainResult:
    """Deterministic chain of `length` transformations starting from one tainted
    source among three clean ones. Ground truth (sources / taint / descendants) is
    tracked by the simulator itself, independently of the system under test."""
    g = ProvenanceGraph(mode=mode); agents = ("agent-A", "agent-B", "agent-C")
    exec_id = f"exec-{mode}-{length}-{attack}-{seed}"
    tainted = g.add_source("src-taint", f"attack:{attack}:{seed}", agent_id="external", execution_id=exec_id, tick=0, taint=(attack,))
    clean = [g.add_source(f"src-clean-{i}", f"clean:{i}:{seed}", agent_id="external", execution_id=exec_id, tick=0) for i in range(3)]
    truth_src: dict[str, set] = {n: {n} for n in g.nodes}; truth_taint: dict[str, set] = {"src-taint": {attack}, **{c.node_id: set() for c in clean}}
    truth_children: dict[str, set] = {n: set() for n in g.nodes}
    prev = tainted; history = [tainted]; survival_hits = 0; false_consensus = 0; detected: list[int] = []; consensus_steps = 0
    for i in range(1, length + 1):
        kind = SCHEDULE[(i - 1) % len(SCHEDULE)]
        agent = agents[i % 3]
        if kind == "summary":
            parents = [prev.node_id, clean[i % 3].node_id]
        elif kind == "majority_vote":
            voters = [h.node_id for h in history[-3:]] if len(history) >= 3 else [prev.node_id, clean[0].node_id, clean[1].node_id]
            parents = voters
        else:
            parents = [prev.node_id]
        node = g.transform(kind, parents, f"{kind}:{i}:{seed}", agent_id=agent, execution_id=exec_id, tick=i, trusted_agent=(agent == "agent-C"), votes=len(parents))
        truth_src[node.node_id] = set().union(*(truth_src[p] for p in parents)); truth_taint[node.node_id] = set().union(*(truth_taint[p] for p in parents))
        truth_children[node.node_id] = set()
        for p in parents:
            truth_children[p].add(node.node_id)
        if set(g.taint(node.node_id)) == truth_taint[node.node_id]:
            survival_hits += 1
        if kind == "majority_vote":
            consensus_steps += 1
            truth_shared = len(parents) > 1 and bool(set.intersection(*(truth_src[p] for p in parents)))
            if truth_shared and not g.shared_source_consensus(parents):
                false_consensus += 1
        if g.taint(node.node_id):
            detected.append(i)
        prev = node; history.append(node)
    final = prev
    # action at tick length+1: authority ONLY through the resolver
    store = store or InMemoryAuthorityStore()
    res = authority_for_action(final, store, principal="operator-A", action="TRANSFER", target="silo-4", scope_digest=scope_digest, state=state, tick=length + 1, grant_ref=grant_ref)
    escalation = 1 if (res.resolved and (grant_ref is None or store.lookup(grant_ref) is None)) else 0
    # containment: roll back from the tainted source
    def truth_desc(n):
        out: set = set(); stack = list(truth_children[n])
        while stack:
            c = stack.pop()
            if c not in out:
                out.add(c); stack.extend(truth_children[c])
        return out
    td = truth_desc("src-taint")
    reached = g.rollback("src-taint", tick=length + 2) - {"src-taint"}
    coverage = len(reached & td) / len(td) if td else 1.0
    truth_final_src = truth_src[final.node_id]; sys_final_src = set(g.sources(final.node_id))
    metrics = {
        "TaintSurvival": survival_hits / length if length else 1.0,
        "SourceAttributionAccuracy": (len(sys_final_src & truth_final_src) / len(sys_final_src | truth_final_src)) if (sys_final_src | truth_final_src) else 1.0,
        "ProvenanceLoss": 1.0 - (len(sys_final_src & truth_final_src) / len(truth_final_src) if truth_final_src else 1.0),
        "TransformationDepth": length,
        "FalseConsensus": false_consensus, "ConsensusSteps": consensus_steps,
        "DelayedAction": 1 if (length + 1 > 10 and attack in truth_taint[final.node_id]) else 0,
        "DelayedActionDetected": 1 if (length + 1 > 10 and g.taint(final.node_id)) else 0,
        "DetectionLatency": (detected[0] if detected else None),
        "ContainmentLatency": (0 if coverage == 1.0 else None),
        "RollbackCoverage": coverage,
        "AuthorityEscalation": escalation,
        "authority_status": res.status, "execution_policy": execution_policy(final),
    }
    return ChainResult(mode, length, attack, metrics, final.node_id, truth_final_src, truth_taint[final.node_id], detected)
