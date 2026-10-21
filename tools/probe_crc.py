"""Try the two editor-style diagrams with their own element types."""
import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

PAIRS = [
    ('CRCCardDiagram', 'CRCCard'),
    ('CRCCardDiagram', 'Class'),
    ('EAProcessStepDiagram', 'ActivityAction'),
    ('EAProcessStepDiagram', 'EAProcessStep'),
    ('EAProcessStepDiagram', 'Action'),
]


def png(path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(24)
    except OSError:
        return (0, 0)
    return struct.unpack('>II', head[16:24]) if head[:8] == b'\x89PNG\r\n\x1a\n' else (0, 0)


def main(project):
    work = tempfile.mkdtemp(prefix='vpce-crc-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    lines = ['$am = ApplicationManager.instance()', '$dm = $am.getDiagramManager()',
             '$f = IModelElementFactory.instance()']
    for index, (dtype, ntype) in enumerate(PAIRS):
        lines.append('$d%d = $dm.createDiagram("%s")' % (index, dtype))
        lines.append('$d%d.setName("e%d")' % (index, index))
        lines.append('$e%d = $f.create("%s")' % (index, ntype))
        lines.append('$e%d.setName("%s")' % (index, ntype))
        lines.append('$s%d = $dm.createDiagramElement($d%d, $e%d)' % (index, index, index))
        lines.append('$s%d.setBounds(60, 60, 160, 90)' % index)
        lines.append('$s%d.setRequestResetCaption(true)' % index)
    lines.append('$am.getProjectManager().saveProject()')
    raw = app.apis().run('\n'.join(lines) + '\n')
    print('\n'.join(ln for ln in raw.splitlines() if ln.startswith('error#')) or 'no errors')

    files = app.projects().render(diagrams=['e%d' % i for i in range(len(PAIRS))],
                                  out=os.path.join(work, 'png'), fmt='png')['files']
    got = {os.path.splitext(f['name'])[0]: f['file'] for f in files}
    for index, (dtype, ntype) in enumerate(PAIRS):
        size = png(got.get('e%d' % index, ''))
        print('%-24s %-16s %s' % (dtype, ntype, '%dx%d' % size if size[0] > 20 else '空图'))
    print('workdir:', work)


if __name__ == '__main__':
    main(sys.argv[1])
