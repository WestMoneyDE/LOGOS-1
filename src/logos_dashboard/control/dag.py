"""Work-order dependency DAG: cycle-free edges, readiness = APPROVED and every mandatory parent settled (VALIDATED | FALSIFIED | SUPERSEDED)."""
from __future__ import annotations

from psycopg.rows import dict_row

SETTLED = ("VALIDATED", "FALSIFIED", "SUPERSEDED")


class CycleError(ValueError):
    pass


def _edges(conn) -> list[tuple[str, str, bool]]:
    with conn.cursor() as cur:
        cur.execute("SELECT child, parent, mandatory FROM ros_work_order_deps"); return [tuple(r) for r in cur.fetchall()]


def _reaches(edges: list[tuple[str, str, bool]], start: str, target: str) -> bool:
    """True when `target` is reachable from `start` following child -> parent edges."""
    parents: dict[str, list[str]] = {}
    for c, p, _ in edges:
        parents.setdefault(c, []).append(p)
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n == target:
            return True
        if n in seen:
            continue
        seen.add(n); stack.extend(parents.get(n, []))
    return False


def add_dependency(conn, child: str, parent: str, mandatory: bool = True, actor: str = "system") -> dict:
    if child == parent:
        raise CycleError("a work order cannot depend on itself")
    edges = _edges(conn)
    if _reaches(edges, parent, child):
        raise CycleError(f"adding {child} -> {parent} would create a cycle")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_work_order_deps (child, parent, mandatory) VALUES (%s, %s, %s) ON CONFLICT (child, parent) DO UPDATE SET mandatory = EXCLUDED.mandatory", (child, parent, mandatory))
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'dag.add_dependency', %s, %s)", (actor, child, '{"parent": "%s", "mandatory": %s}' % (parent, "true" if mandatory else "false")))
    conn.commit()
    return {"child": child, "parent": parent, "mandatory": mandatory}


def graph(conn) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT work_order_id, thesis_id, state, spec->>'question' AS question, approved_at FROM ros_work_orders ORDER BY created_at"); nodes = cur.fetchall()
    edges = [{"child": c, "parent": p, "mandatory": m} for c, p, m in _edges(conn)]
    ready = set(ready_ids(conn))
    for n in nodes:
        n["ready"] = n["work_order_id"] in ready
    # simple layering: depth = longest parent chain
    parents: dict[str, list[str]] = {}
    for e in edges:
        parents.setdefault(e["child"], []).append(e["parent"])
    depth: dict[str, int] = {}
    def d(x: str, guard: int = 0) -> int:
        if x in depth:
            return depth[x]
        depth[x] = 0 if not parents.get(x) or guard > 100 else 1 + max(d(p, guard + 1) for p in parents[x]); return depth[x]
    for n in nodes:
        n["depth"] = d(n["work_order_id"])
    return {"nodes": nodes, "edges": edges}


def ready_ids(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("""SELECT w.work_order_id FROM ros_work_orders w
                       WHERE w.state = 'APPROVED' AND NOT EXISTS (
                           SELECT 1 FROM ros_work_order_deps d JOIN ros_work_orders p ON p.work_order_id = d.parent
                           WHERE d.child = w.work_order_id AND d.mandatory AND p.state <> ALL(%s))
                       ORDER BY w.created_at""", (list(SETTLED),))
        return [r[0] for r in cur.fetchall()]


def blocked(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT w.work_order_id, array_agg(d.parent || ':' || p.state) AS waiting_on FROM ros_work_orders w
                       JOIN ros_work_order_deps d ON d.child = w.work_order_id JOIN ros_work_orders p ON p.work_order_id = d.parent
                       WHERE w.state IN ('APPROVED','BLOCKED') AND d.mandatory AND p.state <> ALL(%s) GROUP BY w.work_order_id""", (list(SETTLED),))
        return cur.fetchall()
