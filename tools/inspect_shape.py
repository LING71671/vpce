"""Print the raw shape XML of a diagram, to compare a hand-made diagram with a
generated one.

    python tools/inspect_shape.py <project.vpp> [--diagram NAME] [--shape DBTable] [--limit 2]

Reads through ExportXML on a temp copy; the source project is untouched.
"""

import argparse
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--diagram')
    parser.add_argument('--shape')
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--attrs-only', action='store_true')
    args = parser.parse_args()

    work = tempfile.mkdtemp(prefix='vpce-inspect-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(args.project, copy)
    app = App(project=copy)
    xml_path = app.projects().export_xml(out_dir=work)['xml']

    root = ET.parse(xml_path).getroot()
    diagrams = root.find('Diagrams')
    printed = 0
    for diagram in diagrams if diagrams is not None else []:
        if args.diagram and diagram.get('Name') != args.diagram:
            continue
        shapes = diagram.find('Shapes')
        if shapes is None:
            continue
        for shape in shapes:
            if args.shape and shape.tag != args.shape:
                continue
            print('=== %s  in diagram %r ===' % (shape.tag, diagram.get('Name')))
            if args.attrs_only:
                for key in sorted(shape.attrib):
                    print('  %-46s %s' % (key, shape.attrib[key]))
            else:
                print(ET.tostring(shape, encoding='unicode')[:4000])
            for child in shape:
                print('  child <%s %s>' % (child.tag, child.attrib))
            printed += 1
            if printed >= args.limit:
                print('\nworkdir:', work)
                return 0
    print('no matching shape; diagrams:', [d.get('Name') for d in (diagrams or [])])
    print('workdir:', work)
    return 0


if __name__ == '__main__':
    sys.exit(main())
