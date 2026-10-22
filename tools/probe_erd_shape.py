"""Does the order of column creation vs shape creation change the export?

    python tools/probe_erd_shape.py <any-project.vpp>

Three orders are tried on the same table definition. In every case the model
ends up identical (two columns on the table); only the sequence differs, which
decides whether the shape's cached column compartment ever sees them.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

HEAD = [
    '$am = ApplicationManager.instance()',
    '$dm = $am.getDiagramManager()',
    '$f = IModelElementFactory.instance()',
    '$d = $dm.createDiagram("ERDiagram")',
    '$d.setName("%NAME%")',
    '$t = $f.create("DBTable")',
    '$t.setName("%TABLE%")',
]

COLS = [
    '$c1 = $t.createDBColumn()',
    '$c1.setName("id")',
    '$c1.setPrimaryKey(true)',
    '$c2 = $t.createDBColumn()',
    '$c2.setName("label")',
]

SHAPE = [
    '$s = $dm.createDiagramElement($d, $t)',
    '$s.setBounds(60, 60, 240, 130)',
    '$s.setRequestResetCaption(true)',
]

CASES = [
    ('cols-then-shape', COLS + SHAPE),
    ('shape-then-cols', SHAPE + COLS),
    ('shape-cols-rebind', SHAPE + COLS + ['$s.setModelElement($t)']),
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


def main(project):
    work = tempfile.mkdtemp(prefix='vpce-erdorder-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    names, errors = [], []
    for label, body in CASES:
        name = 'ord-%s' % label
        names.append(name)
        script = [line.replace('%NAME%', name).replace('%TABLE%', 'T_' + label)
                  for line in HEAD] + body + [
                  '$am.getProjectManager().saveProject()']
        out = app.apis().run('\n'.join(script) + '\n')
        errors += [line for line in out.splitlines() if line.startswith('error#')]

    files = app.projects().render(diagrams=names, out=os.path.join(work, 'png'), fmt='png')['files']
    got = {os.path.splitext(f['name'])[0]: f['file'] for f in files}
    for name in names:
        print('%-22s %s' % (name, '%dx%d' % png_size(got.get(name, ''))))
    if errors:
        print('\nerrors:')
        for line in errors[:8]:
            print(' ', line[:160])
    print('\nworkdir:', work)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
