"""Measure where the wall-clock time goes for one bridge call.

    python tools/bench.py <any-project.vpp>

Breaks a call into: JVM start, VP bootstrap, project open, statement execution.
The project-open step is usually the dominant cost and is only needed for
operations that touch the model.
"""

import base64
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.adapters.runtime import VpRuntime  # noqa: E402

SCRIPT = 'ApplicationManager.instance().getBuildNo()\n'


def timed(label, cmd, cwd):
    started = time.time()
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    elapsed = time.time() - started
    out = proc.stdout.decode('utf-8', 'replace')
    marker = [ln for ln in out.splitlines() if ln.startswith('VPCE_RESP')]
    detail = ''
    if marker:
        detail = base64.b64decode(marker[0][len('VPCE_RESP '):]).decode('utf-8', 'replace')
    detail = detail.strip().splitlines()[-1] if detail.strip() else ''
    print('%-28s %6.2fs  %s' % (label, elapsed, detail[:60]))
    return elapsed


def main(project):
    vp = VpRuntime()
    blob = base64.b64encode(SCRIPT.encode()).decode()

    base = [vp.java, '-Xms256m', '-Xmx1024m', '-Djava.awt.headless=true',
            '-cp', vp.classpath]

    timed('java -version', [vp.java, '-version'], vp.bin)
    timed('plugin, no -project', base + ['com.vp.cmd.Plugin',
                                         '-pluginid', 'com.vpce.bridge',
                                         '-pluginargs', blob], vp.bin)
    timed('plugin, with -project', base + ['com.vp.cmd.Plugin',
                                           '-project', os.path.abspath(project),
                                           '-pluginid', 'com.vpce.bridge',
                                           '-pluginargs', blob], vp.bin)
    timed('export-xml (com.vp.cmd)', base + ['com.vp.cmd.ExportXML',
                                             '-project', os.path.abspath(project),
                                             '-out', os.path.join(os.environ.get('TEMP', '/tmp'),
                                                                  'vpce-bench'),
                                             '-simple'], vp.bin)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
