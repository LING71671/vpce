"""End-to-end test: XML channel, Open API channel, and spec-driven drawing.

    python tests/test_e2e.py <some-project.vpp>

Uses temp copies only; the source project is read, never written.
Takes about a minute -- every step starts a JVM.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402
from vpce.core.spec import Spec  # noqa: E402

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def png_size(path):
    with open(path, 'rb') as fh:
        head = fh.read(24)
    if head[:8] != PNG_MAGIC:
        return None
    return struct.unpack('>II', head[16:24])


def main(source):
    work = tempfile.mkdtemp(prefix='vpce-e2e-')
    project = os.path.join(work, 'probe.vpp')
    shutil.copy2(source, project)
    app = App(project=project)

    print('install :', app.runtime.home)
    print('bridge  :', app.bridge_status()['installed'])
    print('before  :', app.projects().summary()['model_elements'], 'elements')

    # -- 1. XML channel ---------------------------------------------------
    report = app.projects().create_class(
        'XmlProbe', attributes=[('id', 'long')], diagram='Xml Probe Diagram')
    assert not report['missing'], report
    print('xml     : class + diagram verified')

    # -- 2. Open API channel ----------------------------------------------
    info = app.apis().introspect('IDiagramElement')
    assert 'setBounds' in info
    text = app.apis().run(
        '$am = ApplicationManager.instance()\n'
        '$am.getProjectManager().getProject().getName()\n')
    assert 'error#' not in text, text
    print('api     :', text.strip().splitlines()[-1])

    # -- 3. spec-driven drawing -------------------------------------------
    spec = Spec.from_dict({
        'diagram': 'ClassDiagram',
        'name': 'Spec Probe',
        'nodes': [
            {'id': 'a', 'type': 'Class', 'name': 'Alpha',
             'attributes': ['id:long'], 'operations': ['run']},
            {'id': 'b', 'type': 'Class', 'name': 'Beta'},
        ],
        'edges': [{'from': 'a', 'to': 'b', 'type': 'Association', 'name': 'uses'}],
        'layout': {'mode': 'layered'},
    })
    result = app.draw(spec, out=os.path.join(work, 'png'))
    assert not result['verify']['elements_missing'], result['verify']
    assert not result['verify']['diagrams_missing'], result['verify']
    assert result['images'], 'no image produced'
    size = png_size(result['images'][0]['file'])
    assert size and size[0] > 100 and size[1] > 60, size
    print('draw    : diagram %s, %d statements, verified'
          % (result['diagram_id'], result['statements']))
    print('render  : %dx%d px' % size)

    # -- 4. both channels agree -------------------------------------------
    summary = app.projects().summary(refresh=True)
    names = {d['name'] for d in summary['diagrams']}
    assert {'Xml Probe Diagram', 'Spec Probe'} <= names, names
    assert summary['types'].get('Class', 0) >= 3, summary['types']
    print('agree   :', sorted(names))
    print('workdir :', work)
    print('OK')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
