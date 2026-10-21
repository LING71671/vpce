"""Build the vpce bridge plugin.

Visual Paradigm's bundled JRE ships `jdk.compiler` but not `jdk.zipfs`, so
`javac -cp something.jar` fails with "no file system provider handles file".
The workaround is to unpack `openapi.jar` and compile against the directory.

    python java/bridge/build.py [--vp-home DIR]

Output: java/bridge/out/com.vpce.bridge/{plugin.xml, lib/bridge.jar}
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
PLUGIN_ID = 'com.vpce.bridge'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vp-home', default=os.environ.get('VPCE_HOME') or r'E:\Visual Paradigm CE 18.1')
    args = ap.parse_args()

    vp = args.vp_home
    javac = os.path.join(vp, 'jre', 'bin', 'javac.exe')
    if not os.path.isfile(javac):
        print('javac not found at', javac)
        return 2

    api_src = os.path.join(vp, 'lib', 'openapi.jar')
    api_dir = os.path.join(BUILD, 'api')
    if not os.path.isdir(api_dir) or not os.listdir(api_dir):
        os.makedirs(api_dir, exist_ok=True)
        with zipfile.ZipFile(api_src) as z:
            z.extractall(api_dir)

    classes = os.path.join(BUILD, 'classes')
    if os.path.isdir(classes):
        shutil.rmtree(classes)
    os.makedirs(classes, exist_ok=True)

    sources = []
    for root, _dirs, files in os.walk(os.path.join(HERE, 'src')):
        for name in files:
            if name.endswith('.java'):
                sources.append(os.path.join(root, name))

    cmd = [javac, '-encoding', 'UTF-8', '-source', '8', '-target', '8',
           '-cp', api_dir, '-d', classes] + sources
    print('compiling', len(sources), 'file(s)')
    subprocess.run(cmd, check=True)

    out_dir = os.path.join(HERE, 'out', PLUGIN_ID)
    lib_dir = os.path.join(out_dir, 'lib')
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(lib_dir, exist_ok=True)

    jar_path = os.path.join(lib_dir, 'bridge.jar')
    with zipfile.ZipFile(jar_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(classes):
            for name in files:
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, classes).replace('\\', '/'))

    shutil.copy2(os.path.join(HERE, 'plugin.xml'), os.path.join(out_dir, 'plugin.xml'))
    print('built', jar_path, os.path.getsize(jar_path), 'bytes')
    print('plugin', out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
