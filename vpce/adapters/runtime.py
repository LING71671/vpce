"""Locate a Visual Paradigm installation and run its command classes.

The only module in the package that knows about JVMs, classpaths and the
console markers Visual Paradigm prints.
"""

import os
import subprocess
import threading
import time
import zipfile

from ..core.errors import (CommandFailure, ConfigurationError, EditionGate,
                           ProjectLocked, UpgradeRequired)

MARK_EDITION = 'Feature not supported by current edition'
MARK_OLD_PROJECT = 'Please run the script again with "-upgrade-project"'
MARK_LOCKED = 'Project file locked'


class Result(object):
    def __init__(self, command, returncode, output, seconds):
        self.command = command
        self.returncode = returncode
        self.output = output
        self.seconds = seconds

    @property
    def ok(self):
        return self.returncode == 0

    def __repr__(self):
        return '<Result %s rc=%d %.1fs>' % (self.command, self.returncode, self.seconds)


class VpRuntime(object):
    CANDIDATES = (
        r'E:\Visual Paradigm CE 18.1',
        r'C:\Program Files\Visual Paradigm CE 18.1',
        r'C:\Program Files\Visual Paradigm 18.1',
        r'C:\Program Files (x86)\Visual Paradigm CE 18.1',
    )

    def __init__(self, home=None):
        self.home = self._resolve(home)
        self.bin = os.path.join(self.home, 'bin')
        self.java = self._find_java()
        self.classpath = self._build_classpath()
        self._lock = threading.Lock()

    # -- discovery ---------------------------------------------------------

    @classmethod
    def _resolve(cls, home):
        if home:
            home = os.path.abspath(home)
            if not os.path.isdir(home):
                raise ConfigurationError('VP_HOME does not exist: %s' % home)
            return home
        env = os.environ.get('VPCE_HOME') or os.environ.get('VP_HOME')
        if env:
            return os.path.abspath(env)
        for candidate in cls.CANDIDATES:
            if os.path.isdir(candidate):
                return candidate
        raise ConfigurationError(
            'Visual Paradigm not found. Set VPCE_HOME or pass --vp-home.')

    def _find_java(self):
        exe = 'java.exe' if os.name == 'nt' else 'java'
        for rel in (os.path.join('jre', 'bin', exe), os.path.join('jreX', 'bin', exe)):
            path = os.path.join(self.home, rel)
            if os.path.isfile(path):
                return path
        return exe

    def _build_classpath(self):
        parts = []
        libdir = os.path.join(self.home, 'lib')
        if os.path.isdir(libdir):
            for name in sorted(os.listdir(libdir)):
                if name.lower().endswith('.jar'):
                    parts.append(os.path.join(libdir, name))
        for rel in (('ormlib', 'orm.jar'), ('ormlib', 'orm-core.jar'),
                    ('lib', 'xalan.jar'), ('lib', 'jniwrap.jar'),
                    ('lib', 'winpack.jar')):
            path = os.path.join(self.home, *rel)
            if os.path.isfile(path) and path not in parts:
                parts.append(path)
        return os.pathsep.join(['.'] + parts)

    # -- execution ---------------------------------------------------------

    def run(self, command, args, timeout=600, headless=True, check=True):
        cmd = [self.java, '-Xms256m', '-Xmx1024m']
        if headless:
            cmd.append('-Djava.awt.headless=true')
        cmd += ['-cp', self.classpath, 'com.vp.cmd.' + command] + [str(a) for a in args]

        with self._lock:
            started = time.time()
            try:
                proc = subprocess.run(cmd, cwd=self.bin, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise CommandFailure(command, -1, 'timed out after %ss' % timeout)
            output = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
            elapsed = time.time() - started

        result = Result(command, proc.returncode, output, elapsed)
        if MARK_EDITION in output:
            raise EditionGate('%s is not available in this edition' % command)
        if MARK_OLD_PROJECT in output:
            raise UpgradeRequired('project needs -upgrade-project before %s' % command)
        if MARK_LOCKED in output:
            raise ProjectLocked('project is locked by another process')
        if check and (proc.returncode != 0 or 'failed!' in output.lower()):
            raise CommandFailure(command, proc.returncode, output)
        return result

    # -- introspection -----------------------------------------------------

    def describe(self):
        return {
            'home': self.home,
            'java': self.java,
            'jars': len([p for p in self.classpath.split(os.pathsep) if p.endswith('.jar')]),
            'commands': self.available_commands(),
        }

    def available_commands(self):
        found = set()
        for entry in self.classpath.split(os.pathsep):
            if not entry.lower().endswith('.jar'):
                continue
            try:
                with zipfile.ZipFile(entry) as zf:
                    for name in zf.namelist():
                        if name.startswith('com/vp/cmd/') and name.endswith('.class'):
                            base = name[len('com/vp/cmd/'):-len('.class')]
                            if '$' not in base:
                                found.add(base)
            except Exception:
                continue
        return sorted(found)
