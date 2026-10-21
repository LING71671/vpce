"""Dump IDiagramTypeConstants into vpce/core/diagram_types.json.

    python tools/dump_diagram_types.py <any-project.vpp>

Run this again after a Visual Paradigm upgrade; the coverage audit reads the
file, so a new diagram type shows up as "untested" rather than silently
missing.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'vpce', 'core', 'diagram_types.json')


def main(project):
    app = App(project=project)
    text = app.apis().introspect('IDiagramTypeConstants')
    found = {}
    for line in text.splitlines():
        match = re.match(r'\s*\.DIAGRAM_TYPE_(\w+)\s*:\s*String\s*=\s*(.+?)\s*$', line)
        if match:
            found[match.group(2)] = match.group(1)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(found, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print('diagram types:', len(found))
    print('written:', OUT)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
