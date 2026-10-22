"""Does an ERD built through ImportXML keep its column compartment?

    python tools/probe_erd_xml.py <any-project.vpp>

The API route creates a table shape whose exported PNG has no columns. This
writes the same structure as XML and lets Visual Paradigm's own importer build
it, then renders. If columns survive here, the XML channel is the way to build
table-style diagrams.
"""

import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402
from vpce.core.builder import ImportBuilder, new_id  # noqa: E402

XML = """<?xml version="1.0" encoding="UTF-8"?>
<Project Name="probe" UmlVersion="2.x" Xml_structure="simple">
  <Models>
    <DBTable Id="{tbl}" Name="Department">
      <ModelChildren>
        <DBColumn Id="{c1}" Name="deptNo" PrimaryKey="true" Type="integer"
                  Type_internalValue="9" Nullable="true" Unique="false" Index="false"
                  Length="0" Scale="0"/>
        <DBColumn Id="{c2}" Name="deptName" PrimaryKey="false" Type="integer"
                  Type_internalValue="9" Nullable="true" Unique="false" Index="false"
                  Length="0" Scale="0"/>
      </ModelChildren>
    </DBTable>
    <DBTable Id="{tbl2}" Name="Project">
      <ModelChildren>
        <DBColumn Id="{c3}" Name="projNo" PrimaryKey="true" Type="integer"
                  Type_internalValue="9" Nullable="true" Unique="false" Index="false"
                  Length="0" Scale="0"/>
      </ModelChildren>
    </DBTable>
  </Models>
  <Diagrams>
    <ERDiagram Id="{dg}" Name="XML ERD Probe">
      <Shapes>
        <DBTable Id="{s1}" Name="Department" Model="{tbl}" MetaModelElement="{tbl}"
                 X="60" Y="60" Width="240" Height="130" RequestResetCaption="true"
                 ShowColumnsMode="0" ColSortType="0" ShowColumnStereotypes="0"
                 PresentationOption="4" PrimitiveShapeType="0" Selectable="true"
                 ZOrder="0" Background="rgb(245, 182, 122)" Foreground="rgb(0, 0, 0)"/>
        <DBTable Id="{s2}" Name="Project" Model="{tbl2}" MetaModelElement="{tbl2}"
                 X="380" Y="60" Width="240" Height="130" RequestResetCaption="true"
                 ShowColumnsMode="0" ColSortType="0" ShowColumnStereotypes="0"
                 PresentationOption="4" PrimitiveShapeType="0" Selectable="true"
                 ZOrder="1" Background="rgb(245, 182, 122)" Foreground="rgb(0, 0, 0)"/>
      </Shapes>
    </ERDiagram>
  </Diagrams>
</Project>
"""


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
    work = tempfile.mkdtemp(prefix='vpce-erdxml-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)
    app = App(project=copy)

    xml = XML.format(tbl=new_id('t'), tbl2=new_id('u'), c1=new_id('c'), c2=new_id('d'),
                     c3=new_id('e'), dg=new_id('g'), s1=new_id('s'), s2=new_id('s'))
    xml_path = os.path.join(work, 'erd.xml')
    with open(xml_path, 'w', encoding='utf-8') as fh:
        fh.write(xml)

    app.projects().import_file(xml_path)
    summary = app.projects().summary(refresh=True)
    print('diagrams:', [d['name'] for d in summary['diagrams']])
    print('DBTable count:', summary['types'].get('DBTable'), 'DBColumn:',
          summary['types'].get('DBColumn'))

    files = app.projects().render(diagrams='XML ERD Probe', out=os.path.join(work, 'png'),
                                 fmt='png')['files']
    for item in files:
        print('%-24s %s' % (item['name'], '%dx%d' % png_size(item['file'])))
    print('workdir:', work)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
