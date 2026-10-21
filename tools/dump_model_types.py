import os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vpce.app import App

project = sys.argv[1]
app = App(project=project)
txt = app.apis().introspect('IModelElementFactory')
types = {}
for line in txt.splitlines():
    m = re.match(r'\s*\.MODEL_TYPE_(\w+)\s*:\s*String\s*=\s*(.+?)\s*$', line)
    if m:
        types[m.group(2)] = m.group(1)
print('model types:', len(types))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vpce', 'core', 'model_types.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump(types, fh, indent=1, sort_keys=True, ensure_ascii=False)
print('written', os.path.abspath(out))
for k in sorted(types)[:40]:
    print(' ', k, '<-', types[k])
