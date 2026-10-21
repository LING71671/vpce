"""For each diagram type, find which element type actually renders a shape.

    python tools/probe_shape_types.py <any-project.vpp>

Some diagram types ignore an element that the factory happily creates: the
model element lands, the diagram element is returned, but the exported PNG is
empty. This probe tries candidate element types per diagram and reports the
rendered pixel size, so core/profiles.py can be corrected with evidence
instead of guesses.

Works on a temp copy; the source project is untouched.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

CANDIDATES = {
    'ActivityDiagram': ['Action', 'ActivityAction', 'InitialNode', 'ActivityParameterNode',
                        'ActivityObject', 'ActivityFinalNode'],
    'Flowchart': ['Action', 'ActivityAction', 'InitialNode'],
    'StateDiagram': ['State', 'ActionState', 'FinalState', 'InitialNode'],
    'ObjectDiagram': ['Object', 'Class', 'Instance'],
    'CommunicationDiagram': ['Object', 'Actor', 'InteractionActor'],
    'MindMapDiagram': ['MindMapNode', 'MindMap', 'Topic'],
    'InteractionDiagram': ['InteractionLifeLine', 'Lifeline', 'Object'],
    'ComponentDiagram': ['Component', 'ComponentInstance'],
    'DeploymentDiagram': ['Node', 'Artifact'],
    'RequirementDiagram': ['Requirement', 'UserStory'],
    'StateMachineDiagram': ['State'],
    'CompositeStructureDiagram': ['Class', 'Component'],
    'PackageDiagram': ['Package', 'Model'],
    'ClassDiagram': ['Class', 'Interface', 'Enumeration'],
}


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
    work = tempfile.mkdtemp(prefix='vpce-shape-')
    copy = os.path.join(work, 'probe.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    lines = ['$am = ApplicationManager.instance()',
             '$dm = $am.getDiagramManager()',
             '$f = IModelElementFactory.instance()']
    expected = []
    index = 0
    for dtype, types in CANDIDATES.items():
        for ntype in types:
            name = 'p%d' % index
            lines.append('$d%d = $dm.createDiagram("%s")' % (index, dtype))
            lines.append('$d%d.setName("%s")' % (index, name))
            lines.append('$e%d = $f.create("%s")' % (index, ntype))
            lines.append('$e%d.setName("%s")' % (index, ntype))
            lines.append('$s%d = $dm.createDiagramElement($d%d, $e%d)' % (index, index, index))
            lines.append('$s%d.setBounds(60, 60, 160, 90)' % index)
            lines.append('$s%d.setRequestResetCaption(true)' % index)
            expected.append((name, dtype, ntype))
            index += 1
    lines.append('$am.getProjectManager().saveProject()')
    raw = app.apis().run('\n'.join(lines) + '\n')
    errors = [ln for ln in raw.splitlines() if ln.startswith('error#')]

    files = app.projects().render(diagrams=[e[0] for e in expected],
                                  out=os.path.join(work, 'png'), fmt='png')['files']
    by_name = {os.path.splitext(f['name'])[0]: f['file'] for f in files}

    current = None
    for name, dtype, ntype in expected:
        if dtype != current:
            print('\n%s' % dtype)
            current = dtype
        size = png_size(by_name.get(name, '')) if name in by_name else (0, 0)
        print('  %-22s %s' % (ntype, '%dx%d' % size if size[0] > 20 else '空图'))

    if errors:
        print('\nerrors (%d):' % len(errors))
        for line in errors[:10]:
            print(' ', line[:140])
    print('\nworkdir:', work)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
