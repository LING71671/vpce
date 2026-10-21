"""Try alternative construction paths for element types create() refuses.

Some types are refused by the generic `create(String)` but are reachable from a
parent (`createChild`) or from their own factory method. This decides whether a
type is "unsupported" or merely "needs a parent".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402

TYPES = ['Sprint', 'UseCaseStatement', 'UserStory', 'UserStoryConfirmation',
         'Enumeration', 'Interface', 'State', 'Object', 'Action', 'MindMapNode']

script = '''$am = ApplicationManager.instance()
$f = IModelElementFactory.instance()
$pkg = $f.create("Package")
$pkg.setName("probe-pkg")
$parent = $pkg.createChild("Class")
$parent.setName("probe-parent")
'''

for index, name in enumerate(TYPES):
    script += '$a%d = $f.create("%s")\n' % (index, name)
for index, name in enumerate(TYPES):
    script += '$b%d = $parent.createChild("%s")\n' % (index, name)
for index, name in enumerate(TYPES):
    script += '$c%d = $pkg.createChild("%s")\n' % (index, name)


def main(project):
    app = App(project=project)
    out = app.apis().run(script)
    print(out)
    print('---')
    for line in out.splitlines():
        if line.startswith('error#'):
            print(line)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
