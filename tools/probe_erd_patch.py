"""Test whether the missing diagram-level column options are what hides the columns.

    python tools/probe_erd_patch.py <project-with-a-generated-ERD.vpp> "<diagram name>"

Copies the project, injects the flag set that a GUI-created ERDiagram carries
into that diagram's DEFINITION blob, then renders it. Read the printed PNG path
and look at it.

This is a diagnostic, not a supported write path.
"""

import os
import re
import shutil
import sqlite3
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

FLAGS = ('_alignColumnProperties=T;\n\t_showExtraColumnProperties=T;\n'
         '\t_showColumnTypes=T;\n\t_showColumnNullable=T;\n'
         '\t_showColumnDefaultValue=F;\n\t_showColumnUniqueConstraintName=F;\n'
         '\t_showColumnUserType=F;\n\t_columnConstraintsDisplayOption=2;\n'
         '\t_pointForeignKeyEndToColumn=F;\n\tshowSchemaName=T;\n')


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
    work = tempfile.mkdtemp(prefix='vpce-erdpatch-')
    copy = os.path.join(work, 'p.vpp')
    shutil.copy2(project, copy)

    con = sqlite3.connect(copy)
    row = con.execute('select ID, DEFINITION from DIAGRAM where NAME=?',
                      (diagram_name,)).fetchone()
    if row is None:
        print('diagram not found:', diagram_name)
        print('available:', [r[0] for r in con.execute('select NAME from DIAGRAM')])
        return 2
    diag_id, blob = row
    text = blob.decode('utf-8', 'replace') if isinstance(blob, bytes) else blob
    before = len(text)
    patched = re.sub(r'(\{\s*\n\t)', r'\1' + FLAGS.replace('\\', '\\\\'), text, count=1)
    con.execute('update DIAGRAM set DEFINITION=? where ID=?',
                (patched.encode('utf-8'), diag_id))
    con.commit()
    con.close()
    print('patched %s: %d -> %d bytes' % (diag_id, before, len(patched)))

    app = App(project=copy)
    files = app.projects().render(diagrams=diagram_name, out=os.path.join(work, 'png'),
                                 fmt='png')['files']
    for item in files:
        print('%-30s %s' % (item['name'], '%dx%d' % png_size(item['file'])))
        print('open:', item['file'])
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
