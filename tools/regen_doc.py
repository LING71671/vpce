"""Regenerate COVERAGE.md from the existing coverage.json without re-probing."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import coverage  # noqa: E402

with open(os.path.join(ROOT, 'coverage.json'), encoding='utf-8') as fh:
    data = json.load(fh)

detail = data['render']['detail']
data['render']['ok'] = sum(1 for v in detail.values() if v.get('rendered'))
data['render']['native'] = sum(1 for v in detail.values()
                               if v.get('rendered') and v.get('role') == 'native')

with open(os.path.join(ROOT, 'COVERAGE.md'), 'w', encoding='utf-8') as fh:
    fh.write(coverage.render_doc(data))

print('render %d/%d, native %d' % (data['render']['ok'], data['render']['total'],
                                   data['render']['native']))
for dtype, info in sorted(detail.items()):
    if not info.get('rendered'):
        print('  no shape:', dtype, info.get('node_type'))
