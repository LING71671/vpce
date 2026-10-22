"""Check what makes an ERD table render its columns in a headless export.

    python tools/probe_erd_columns.py <any-project.vpp>

Builds three tables that differ only in the shape options applied, renders the
diagram and reports the PNG size of each. If only one of them grows, that
option is the switch.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

CASES = [
    ('follow=0', ['setShowColumnsMode(0)']),
    ('all=1', ['setShowColumnsMode(1)']),
    ('pk=4', ['setShowColumnsMode(4)']),
    ('all+fit', ['setShowColumnsMode(1)', 'setRequestFitSize(true)']),
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
    work = tempfile.mkdtemp(prefix='vpce-erd-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    lines = ['$am = ApplicationManager.instance()',
             '$dm = $am.getDiagramManager()',
             '$f = IModelElementFactory.instance()']
    names = []
    for index, (label, ops) in enumerate(CASES):
        name = 'erd-%s' % label
        names.append(name)
        lines += [
            '$d%d = $dm.createDiagram("ERDiagram")' % index,
            '$d%d.setName("%s")' % (index, name),
            '$t%d = $f.create("DBTable")' % index,
            '$t%d.setName("T_%s")' % (index, label.replace('+', '_')),
            '$c%d0 = $t%d.createDBColumn()' % (index, index),
            '$c%d0.setName("id")' % index,
            '$c%d0.setPrimaryKey(true)' % index,
            '$c%d1 = $t%d.createDBColumn()' % (index, index),
            '$c%d1.setName("label")' % index,
            '$s%d = $dm.createDiagramElement($d%d, $t%d)' % (index, index, index),
            '$s%d.setBounds(%d, 60, 240, 130)' % (index, 60 + index * 300),
            '$s%d.setRequestResetCaption(true)' % index,
        ] + ['$s%d.%s' % (index, op) for op in ops]
    lines.append('$am.getProjectManager().saveProject()')
    out = app.apis().run('\n'.join(lines) + '\n')
    errors = [line for line in out.splitlines() if line.startswith('error#')]

    files = app.projects().render(diagrams=names, out=os.path.join(work, 'png'), fmt='png')['files']
    got = {os.path.splitext(f['name'])[0]: f['file'] for f in files}
    for index, (label, _) in enumerate(CASES):
        size = png_size(got.get(names[index], ''))
        print('%-16s %s' % (label, '%dx%d' % size))
    if errors:
        print('\nerrors:')
        for line in errors[:6]:
            print(' ', line[:160])
    print('\nworkdir:', work)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
