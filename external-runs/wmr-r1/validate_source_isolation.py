#!/usr/bin/env python3
import ast, sys
from pathlib import Path

p=Path(sys.argv[1])
tree=ast.parse(p.read_text())
bad=[]
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for n in node.names:
            if n.name.split(".")[0] in {"arc_agi","arcengine"}:
                bad.append(("import",n.name))
    elif isinstance(node, ast.ImportFrom):
        if (node.module or "").split(".")[0] in {"arc_agi","arcengine"}:
            bad.append(("from",node.module))
text=p.read_text().lower()
for token in ["metadata.json","environment_files/","environment_files\\"]:
    if token in text:
        bad.append(("text",token))
if bad:
    print("FAIL",bad)
    raise SystemExit(1)
print("PASS evaluator source isolation")
