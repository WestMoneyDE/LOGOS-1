import os
"""Semantic gold labels for every distinct Laya decision question in the Keystone R1 run.

Labels are derived mechanically from the logs (goal text, option labels, state text, step URLs
and actions) by the rules written below. They are not human annotations.
"""
import json, re, math, collections

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keystone-r1-run")  # `dvc pull` restores it
TASKS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(D, "tasks.jsonl"), encoding="utf-8")}
CALLS = [json.loads(l) for l in open(os.path.join(D, "calls.jsonl"), encoding="utf-8")]
STEPS = [json.loads(l) for l in open(os.path.join(D, "steps.jsonl"), encoding="utf-8")]
STEP = {(s["task"], s["tick"]): s for s in STEPS}
LAYA = [c for c in CALLS if c["kind"] == "laya" and c["purpose"] == "decision"]

MIN_CONF, GAP = 0.4, 0.15   # jev_ultrafast/graph.py JEV_MIN_CONFIDENCE_DEFAULT / JEV_AMBIGUITY_GAP_DEFAULT


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - s), 3), round(min(1, c + s), 3)]


def top_gap(probs):
    v = sorted(probs.values(), reverse=True)
    return (v[0], (v[0] - v[1]) if len(v) > 1 else None)


def ambiguous(probs):
    t, g = top_gap(probs)
    return g is not None and t < MIN_CONF and g < GAP


ROLES = ("link", "button", "textbox", "checkbox", "radio", "combobox", "option", "menuitem", "tab", "switch")


def strip_role(label):
    parts = label.split(" ", 1)
    if parts[0] in ROLES and len(parts) == 2:
        return parts[0], parts[1]
    return None, label


def norm(s):
    s = s.replace("\u2190", " ").replace("\u2192", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


# ---------------------------------------------------------------- item / next targets
# Click targets quoted in each goal. Tasks listed in NEXT_UNLABELLED have a navigational
# precondition or an unquoted target that the logs do not settle.
def click_targets(tid):
    goal = TASKS[tid]["goal"]
    manual = {
        "nav-settings": ["Architect"],
        "fn-search": ["Pods und Lebenszyklen"],
        "fn-home-domain-progress": ["AWS architecture"],
        "fn-domain-article": ["Deployments und ReplicaSets"],
        "fn-article-requires": ["CRI und Container-Runtimes"],
        "fn-article-back": ["Kubernetes, containers & platform engineering"],
        "fn-article-news": ["Keine aktuellen News", "aktuelle News zu diesem Thema"],
        "fn-roles-open": ["Platform Architect"],
        "fn-role-test-start": ["Test starten"],
        "fn-srs-random": ["Zufällig", "Antwort anzeigen"],
        "fn-srs-rate": ["Zufällig", "Antwort anzeigen", "Gut"],
        "fn-srs-learned": ["Gelerntes"],
        "fn-chat-article": ["Assistent öffnen"],
        "fn-settings-provider-check": ["Claude Code CLI", "Verfügbarkeit prüfen"],
        "fn-settings-export": ["Fortschritt exportieren"],
    }
    if tid in manual:
        return manual[tid]
    q = re.findall(r'"([^"]+)"', goal)
    return [q[-1]] if q else []


NEXT_UNLABELLED = {
    "fn-home-next-article": "goal names no quoted click target ('first recommended article'); 'link Home' may be a valid route",
    "fn-roles-star": "page is /roles/GENAI; goal says 'on the roles page', and '← Alle Rollen' is offered as a route back",
    "fn-role-panel-article": "multi-step goal; which article is 'first in the panel' is not in the logs",
    "fn-settings-import-view": "profile link is offered under the renamed label 'Claude Code CLI' (jev mis-fill); a valid route",
}


def names_target(label, target):
    role, name = strip_role(label)
    n, t = norm(name), norm(target)
    if role == "textbox":
        return False
    if n == t:
        return True
    # A link whose accessible name starts with the target and continues with card metadata
    # (article cards "X KB-0385 ...", role cards "X zu bevorzugten Rollen hinzufügen ... X").
    return role == "link" and n.startswith(t + " ")


def label_item_next(task, qid, crit, calls):
    if qid == "next" and task in NEXT_UNLABELLED:
        return dict(status="unlabelled", reason=NEXT_UNLABELLED[task])
    targets = click_targets(task)
    if not targets:
        return dict(status="unlabelled", reason="no click target quoted in goal")
    if qid == "item":
        m = re.match(r"Which element opens (.*)\?$", calls[0]["request"]["questions"][qid]["instructions"])
        if m and any(norm(m.group(1)) == norm(t) for t in targets):
            targets = [t for t in targets if norm(t) == norm(m.group(1))]
    gold = [k for k, v in crit.items() if k != "none" and any(names_target(v, t) for t in targets)]
    flags = []
    labs = [strip_role(v)[1] for v in crit.values()]
    if set(labs) == {"Reload", "Back"}:
        flags.append("error_page_recovery_offered")
    if gold:
        return dict(status="labelled", gold=gold, gold_present=True, targets=targets, flags=flags,
                    reason="option label equals/names the goal's quoted target")
    return dict(status="labelled", gold=["none"] if "none" in crit else [], gold_present=False,
                targets=targets, flags=flags, reason="no offered option names the goal's quoted target")


# ---------------------------------------------------------------- holds
def label_holds(state, crit):
    m = re.match(r"Form field: (.*)$", state.strip(), re.S)
    field = m.group(1) if m else state
    value = field.split(" = ", 1)[1].strip() if " = " in field else None
    reqs = {k: v.split(" = ", 1)[1].strip() for k, v in crit.items() if k != "none" and " = " in v}
    if value in (None, "", "(empty)"):
        return dict(status="labelled", gold=["none"], gold_present=False, field_value=value,
                    reason="field is empty or has no value; it holds no requirement")
    gold = [k for k, v in reqs.items() if v == value]
    if gold:
        return dict(status="labelled", gold=gold, gold_present=True, field_value=value,
                    reason="requirement value equals field value")
    return dict(status="labelled", gold=["none"], gold_present=False, field_value=value,
                reason="field value equals no requirement value")


# ---------------------------------------------------------------- field
def label_field(state, crit):
    m = re.match(r"Requirement: (.*?) = (.*)$", state.strip(), re.S)
    what = m.group(1).strip() if m else ""
    gold = [k for k, v in crit.items() if norm(what) and norm(what) in norm(strip_role(v)[1].split(" = ")[0])]
    if gold:
        return dict(status="labelled", gold=gold, gold_present=True, reason="option names the requirement's field")
    return dict(status="labelled", gold=[], gold_present=False,
                reason="no offered element is the requirement's control (search/Anzeigename textboxes, chat buttons)")


# ---------------------------------------------------------------- set / option
def label_set(state, crit):
    m = re.match(r"Requirement: (.*?) = (.*)$", state.strip(), re.S)
    value = m.group(2).strip() if m else ""
    match = [k for k, v in crit.items() if k != "none" and norm(strip_role(v)[1]) == norm(value)]
    if match:
        roles = {strip_role(crit[k])[0] for k in match}
        if roles <= {"link", "button"}:
            return dict(status="unlabelled", reason="an offered link/button carries the value's name, but it is "
                        "navigation (sidebar); whether it 'sets' the requirement is not settled by the logs")
        return dict(status="labelled", gold=match, gold_present=True, reason="form control carries the value")
    return dict(status="labelled", gold=["none"] if "none" in crit else [], gold_present=False,
                reason="no offered element carries the requirement value")


# ---------------------------------------------------------------- met
STATE_WORDS = {"checked", "unchecked", "dark mode", "light mode", "on", "off", "selected"}


def label_met(state):
    m = re.match(r"Requirement: (.*?) = (.*?)\nCurrent value: (.*)$", state.strip(), re.S)
    if not m:
        return dict(status="unlabelled", reason="unparsed")
    what, val, cur = (x.strip() for x in m.groups())
    if cur == val:
        return dict(status="labelled", gold=["yes"], gold_present=True, reason="current value equals requirement literally")
    if val.casefold() in STATE_WORDS:
        return dict(status="unlabelled", reason="requirement is a state word (%r); current value %r is an element label, "
                    "not a state reading" % (val, cur[:40]))
    if cur and cur != what:
        return dict(status="labelled", gold=["no"], gold_present=True, reason="text requirement; current text differs literally")
    return dict(status="unlabelled", reason="current value is the element's own label")


# ---------------------------------------------------------------- done
def label_done(task, tick, state):
    s = STEP.get((task, tick), {})
    url = s.get("url") or ""
    path = re.sub(r"^https?://[^/]+", "", url)
    if task == "nav-collapse":
        act = s.get("action")
        if act == "Expand sidebar":
            return dict(status="labelled", truth=True, reason="the sidebar button at this tick reads 'Expand sidebar' (collapsed)")
        if act == "Collapse sidebar":
            return dict(status="labelled", truth=False, reason="the sidebar button at this tick reads 'Collapse sidebar' (expanded)")
        prev = STEP.get((task, tick - 1), {})
        if prev.get("action") == "Collapse sidebar" and prev.get("page_changed"):
            return dict(status="labelled", truth=True, reason="previous tick clicked 'Collapse sidebar' and the page changed")
        return dict(status="unlabelled", reason="sidebar button state not logged at this tick")
    if task == "fn-role-test-start":
        if "Deine Antwort" in state:
            return dict(status="labelled", truth=True, reason="answer box of the test is visible")
        if "Test wird vorbereitet" in state:
            return dict(status="labelled", truth=False, reason="page shows 'Test wird vorbereitet…' (not started)")
        if not path.startswith("/roles/STAFF/test"):
            return dict(status="labelled", truth=False, reason="URL %s is not the test page" % path)
        return dict(status="unlabelled", reason="test page, start state not visible in state text")
    if task == "fn-role-panel-article":
        if not path.startswith("/articles/"):
            return dict(status="labelled", truth=False, reason="URL %s is not an article page" % path)
        return dict(status="unlabelled", reason="article page; whether it is the panel's first article is not logged")
    return dict(status="unlabelled", reason="finish condition not decidable from URL/state (%s)" % path)


# ---------------------------------------------------------------- submit
REAL_SUBMIT = {"Speichern", "Antwort einreichen", "Weiter"}
CHROME = {"Toggle theme", "Assistent öffnen", "Collapse sidebar", "Expand sidebar", "Chat schließen"}


def label_submit(task, crit):
    names = {k: strip_role(v)[1] for k, v in crit.items()}
    gold = [k for k, n in names.items() if n in REAL_SUBMIT]
    other = [n for n in names.values() if n not in REAL_SUBMIT | CHROME]
    if gold:
        goal = TASKS[task]["goal"]
        flags = [] if any('"%s"' % names[k] in goal for k in gold) else ["submit_not_named_in_goal"]
        return dict(status="labelled", gold=gold, gold_present=True, flags=flags,
                    reason="a real submit control is offered")
    if other:
        return dict(status="unlabelled", reason="non-chrome, non-submit control offered: %s" % other)
    return dict(status="labelled", gold=[], gold_present=False, reason="only UI chrome offered")


# ---------------------------------------------------------------- build rows
def kind_of(qid):
    return qid.split("_")[0]


def build():
    groups = collections.OrderedDict()
    for c in LAYA:
        (qid, q), = c["request"]["questions"].items()
        kind = kind_of(qid)
        crit = json.dumps(q["criteria"], ensure_ascii=False, sort_keys=True)
        key = (c["task"], qid, crit)
        if kind in ("done", "met"):
            key = key + (c["request"]["state"],)
        groups.setdefault(key, []).append(c)
    rows = []
    for key, cs in groups.items():
        c0 = cs[0]
        (qid, q), = c0["request"]["questions"].items()
        kind, crit, state, task = kind_of(qid), q["criteria"], c0["request"]["state"], c0["task"]
        n_opt = len(crit)
        if n_opt < 2:
            lab = dict(status="unlabelled", reason="single option: no choice to make (probability 1.0 by construction)",
                       degenerate=True)
        elif kind in ("item", "next"):
            lab = label_item_next(task, qid, crit, cs)
        elif kind == "holds":
            lab = label_holds(state, crit)
        elif kind == "field":
            lab = label_field(state, crit)
        elif kind in ("set", "option"):
            lab = label_set(state, crit)
        elif kind == "met":
            lab = label_met(state)
        elif kind == "done":
            ticks = [x["tick"] for x in cs]
            labs = [label_done(task, t, state) for t in ticks]
            # One row per distinct state text. Every tick that showed this state must be
            # labelled and agree; otherwise the row is unlabelled.
            truths = {l.get("truth") for l in labs}
            if all(l["status"] == "labelled" for l in labs) and len(truths) == 1:
                lab = dict(labs[0])
            elif len(truths - {None}) > 1:
                lab = dict(status="unlabelled", reason="same state text at ticks with different truth: %s"
                           % [(t, l.get("truth")) for t, l in zip(ticks, labs)],
                           state_insufficient=True)
            else:
                lab = dict(status="unlabelled", reason="; ".join(sorted({l["reason"] for l in labs if l["status"] == "unlabelled"})))
            if lab["status"] == "labelled":
                lab = dict(lab, gold=["finish"] if lab["truth"] else [k for k in crit if k != "finish"],
                           gold_present=True)
        elif kind == "submit":
            lab = label_submit(task, crit)
        else:
            lab = dict(status="unlabelled", reason="unknown kind")
        ans = c0["response"]["answers"][qid]
        probs = ans["probabilities"]
        t, g = top_gap(probs)
        choices = [x["response"]["answers"][qid]["choice"] for x in cs]
        row = dict(task=task, qid=qid, kind=kind, ticks=[x["tick"] for x in cs], n_calls=len(cs),
                   instructions=q["instructions"], criteria=crit, state=state, n_options=n_opt,
                   none_offered="none" in crit, choice=ans["choice"], choice_label=crit.get(ans["choice"]),
                   probabilities=probs, top=t, gap=g, gate_fires=ambiguous(probs),
                   choices_all_calls=choices, choices_vary=len(set(choices)) > 1, **lab)
        if row["status"] == "labelled":
            gold = set(row.get("gold") or [])
            row["correct"] = row["choice"] in gold if gold else None   # None: no option is correct
            row["chose_none"] = row["choice"] == "none"
        rows.append(row)
    return rows


if __name__ == "__main__":
    rows = build()
    print(len(rows))
    print(collections.Counter((r["kind"], r["status"]) for r in rows))
