"""Add two tables to a GUI-made ERD and see whether their columns render.

    python tools/probe_erd_mix.py <gui-made-erd.vpp> "<diagram name>"

If the two existing tables draw their columns and the two added ones do not,
the exporter is fine and the creation path is what loses the column rows.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

SCRIPT = '''$am = ApplicationManager.instance()
$dm = $am.getDiagramManager()
$f = IModelElementFactory.instance()
$p = $am.getProjectManager().getProject()
$d = $p.getDiagramById($diagramId)
$t1 = $f.create("DBTable")
$t1.setName("T_API")
$c = $t1.createDBColumn()
$c.setName("col_a")
$s1 = $dm.createDiagramElement($d, $t1)
$s1.setBounds(60, 220, 240, 130)
$s1.setRequestResetCaption(true)
$t2 = $f.create("DBTable")
$t2.setName("T_TYPE")
$c2 = $t2.createDBColumn()
$c2.setName("col_b")
$s2 = $dm.createDiagramElement($d, "DBTable")
$s2.setModelElement($t2)
$s2.setBounds(380, 220, 240, 130)
$s2.setRequestResetCaption(true)
$am.getProjectManager().saveProject()
'''


def png_size(path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(24)
    except OSError:
        return (0, 0)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return (0, 0)
    return struct.unpack('>II', head[16:24])


def main(project, diagram_name):
    work = tempfile.mkdtemp(prefix='vpce-erdmix-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    diagram_id = None
    for item in app.projects().diagrams(refresh=True):
        if item['name'] == diagram_name:
            diagram_id = item['id']
    if not diagram_id:
        print('diagram not found:', diagram_name)
        return 2

    out = app.apis().run(SCRIPT.replace('$diagramId', '"%s"' % diagram_id))
    errors = [line for line in out.splitlines() if line.startswith('error#')]
    if errors:
        print('errors:', errors[:4])

    files = app.projects().render(diagrams=diagram_name, out=os.path.join(work, 'png'),
                                 fmt='png')['files']
    for item in files:
        print('%-34s %s' % (item['name'], '%dx%d' % png_size(item['file'])))
        print('open:', item['file'])
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
