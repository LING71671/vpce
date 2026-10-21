"""Find, per supported diagram type, an element type that actually renders.

    python tools/find_shapes.py <any-project.vpp> [--rounds N]

Round-based: every round gives each still-unsolved diagram type one more
candidate, creates the diagram + one shape, saves, renders everything and
checks which PNGs are non-empty. Stops when every type is solved or the
candidate pool runs out.

Output is printed as a Python dict you can paste into tools/coverage.py.
"""

import argparse
import json
import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: tried in this order, one per round
POOL = [
    'Class', 'Component', 'Node', 'Package', 'Actor', 'UseCase', 'ActivityAction',
    'InitialNode', 'State', 'InteractionLifeLine', 'DBTable', 'Requirement',
    'Object', 'Artifact', 'Interface', 'Enumeration', 'ChenERDEntity', 'Action',
    'ActivityFinalNode', 'DFProcess', 'Entity', 'MindMapNode', 'FinalState',
    'Controller', 'Boundary', 'Screen', 'WireflowScreen', 'UserStory',
]


def png_size(path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(24)
    except OSError:
        return (0, 0)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return (0, 0)
    return struct.unpack('>II', head[16:24])


def supported_types(project):
    path = os.path.join(ROOT, 'coverage.json')
    if not os.path.isfile(path):
        raise SystemExit('coverage.json not found; run tools/coverage.py first')
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    detail = data['diagram_types']['detail']
    return [name for name, value in sorted(detail.items()) if value[0] == 'ok']


def run_round(app, project, pairs, work, round_no):
    """pairs: [(diagram_type, element_type)]. Returns {diagram_type: (ntype, px)}."""
    lines = ['$am = ApplicationManager.instance()',
             '$dm = $am.getDiagramManager()',
             '$f = IModelElementFactory.instance()']
    names = []
    for index, (dtype, ntype) in enumerate(pairs):
        name = 's%d_%d' % (round_no, index)
        names.append(name)
        lines.append('$d%d = $dm.createDiagram("%s")' % (index, dtype))
        lines.append('$d%d.setName("%s")' % (index, name))
        lines.append('$e%d = $f.create("%s")' % (index, ntype))
        lines.append('$e%d.setName("%s")' % (index, ntype))
        lines.append('$s%d = $dm.createDiagramElement($d%d, $e%d)' % (index, index, index))
        lines.append('$s%d.setBounds(60, 60, 160, 90)' % index)
        lines.append('$s%d.setRequestResetCaption(true)' % index)
    lines.append('$am.getProjectManager().saveProject()')
    raw = app.apis().run('\n'.join(lines) + '\n')
    errors = sum(1 for line in raw.splitlines() if line.startswith('error#'))

    files = app.projects().render(diagrams=names, out=work, fmt='png')['files']
    by_name = {os.path.splitext(f['name'])[0]: f['file'] for f in files}
    out = {}
    for index, (dtype, ntype) in enumerate(pairs):
        size = png_size(by_name.get('s%d_%d' % (round_no, index), ''))
        out[dtype] = (ntype, size, size[0] > 20)
    return out, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--rounds', type=int, default=6)
    args = parser.parse_args()

    types = supported_types(args.project)
    print('supported diagram types:', len(types))

    work = tempfile.mkdtemp(prefix='vpce-shapes-')
    project = os.path.join(work, 'probe.vpp')
    shutil.copy2(args.project, project)
    app = App(project=project)

    winners = {}
    for round_no in range(args.rounds):
        pending = [t for t in types if t not in winners]
        if not pending:
            break
        ntype = POOL[round_no % len(POOL)]
        pairs = [(t, ntype) for t in pending]
        result, errors = run_round(app, project, pairs, os.path.join(work, 'r%d' % round_no),
                                   round_no)
        solved = [t for t, (_, _, ok) in result.items() if ok]
        for t in solved:
            winners[t] = (result[t][0], result[t][1])
        print('round %d  candidate=%-20s solved=%2d  remaining=%2d  errors=%d'
              % (round_no + 1, ntype, len(solved), len(types) - len(winners), errors))

    print()
    print('WINNERS = {')
    for dtype in sorted(winners):
        ntype, size = winners[dtype]
        print("    '%-28s: '%-20s  # %dx%d" % (dtype + "':", ntype + "',", size[0], size[1]))
    print('}')
    missing = [t for t in types if t not in winners]
    if missing:
        print()
        print('unsolved (%d): %s' % (len(missing), ', '.join(missing)))
    print('workdir:', work)
    return 0


if __name__ == '__main__':
    sys.exit(main())
