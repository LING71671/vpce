"""Open API adapter: ships statements to the `com.vpce.bridge` plugin.

Implements `ports.Api`. The bridge itself is built from `java/bridge` and has
to be installed once into the Visual Paradigm plugin directory; everything
below that is transport detail.
"""

import base64
import os
import shutil
import tempfile

from ..core.errors import CommandFailure, ConfigurationError, VpceError

PLUGIN_ID = 'com.vpce.bridge'
MARKER = 'VPCE_RESP '
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT)
BUILT_PLUGIN = os.path.join(PROJECT_ROOT, 'java', 'bridge', 'out', PLUGIN_ID)


def plugin_root():
    appdata = os.environ.get('APPDATA')
    if not appdata:
        raise ConfigurationError('APPDATA is not set; cannot locate the plugin directory')
    return os.path.join(appdata, 'VisualParadigm', 'plugins')


def install(force=False):
    if not os.path.isdir(BUILT_PLUGIN):
        raise ConfigurationError('plugin not built: %s (run java/bridge/build.py)'
                                 % BUILT_PLUGIN)
    target = os.path.join(plugin_root(), PLUGIN_ID)
    if os.path.isdir(target) and not force:
        return {'installed': False, 'path': target, 'reason': 'already present'}
    os.makedirs(os.path.join(target, 'lib'), exist_ok=True)
    shutil.copy2(os.path.join(BUILT_PLUGIN, 'plugin.xml'), os.path.join(target, 'plugin.xml'))
    for name in os.listdir(os.path.join(BUILT_PLUGIN, 'lib')):
        shutil.copy2(os.path.join(BUILT_PLUGIN, 'lib', name), os.path.join(target, 'lib', name))
    return {'installed': True, 'path': target}


def uninstall():
    target = os.path.join(plugin_root(), PLUGIN_ID)
    if os.path.isdir(target):
        shutil.rmtree(target)
        return {'removed': True, 'path': target}
    return {'removed': False, 'path': target}


def is_installed():
    try:
        return os.path.isfile(os.path.join(plugin_root(), PLUGIN_ID, 'plugin.xml'))
    except ConfigurationError:
        return False


def needs_project(script):
    """True unless every statement is a discovery directive.

    `@introspect` and `@search` read class metadata; they do not touch the
    project, and opening one costs several seconds.
    """
    for line in script.splitlines():
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('#'):
            continue
        if not line.startswith('@'):
            return True
    return False


class OpenApi(object):
    """Talks to the bridge plugin.

    A call costs a JVM start plus a Visual Paradigm bootstrap plus a project
    open -- 20-40 s on a small file, and `-project` is mandatory for
    `com.vp.cmd.Plugin`. Two things keep that bearable: discovery directives
    are cached per build, and one call can carry any number of statements.
    """

    def __init__(self, runtime, project_path):
        self.runtime = runtime
        self.project_path = project_path

    # -- discovery cache ---------------------------------------------------

    @property
    def cache_dir(self):
        return os.path.join(tempfile.gettempdir(), 'vpce-cache', 'bridge')

    def _cache_key(self, script):
        import hashlib
        try:
            stat = os.stat(os.path.join(self.runtime.home, 'lib', 'openapi.jar'))
            build = '%s:%s' % (stat.st_size, stat.st_mtime_ns)
        except OSError:
            build = 'unknown'
        raw = '%s|%s|%s' % (self.runtime.home, build, script)
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    def _cached(self, script, timeout, refresh=False):
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, self._cache_key(script) + '.txt')
        if not refresh and os.path.isfile(path):
            with open(path, encoding='utf-8') as fh:
                return fh.read()
        text = self.run_script(script, timeout)
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)
        except OSError:
            pass
        return text

    # -- invocation --------------------------------------------------------

    def _invoke(self, blob, timeout):
        result = self.runtime.run('Plugin', ['-project', self.project_path,
                                             '-pluginid', PLUGIN_ID,
                                             '-pluginargs', blob],
                                  timeout=timeout, check=False)
        output = result.output or ''
        for line in output.splitlines():
            if line.startswith(MARKER):
                return (base64.b64decode(line[len(MARKER):].strip())
                        .decode('utf-8', 'replace'), output)
        return None, output

    # -- public ------------------------------------------------------------

    def run_script(self, script, timeout=900):
        if not script.endswith('\n'):
            script += '\n'
        blob = base64.b64encode(script.encode('utf-8')).decode('ascii')
        text, output = self._invoke(blob, timeout)
        if text is not None:
            return text
        if 'Plugin not found' in output:
            raise VpceError('bridge plugin not installed; run: vpce bridge --install')
        if 'ClassNotFoundException' in output:
            raise ConfigurationError('bridge class failed to load; check '
                                     'plugin.xml + lib/bridge.jar layout')
        raise CommandFailure('Plugin(bridge)', 0, output)

    def introspect(self, class_name, timeout=900, refresh=False):
        return self._cached('@introspect %s\n' % class_name, timeout,
                            refresh=refresh).strip()

    def introspect_many(self, class_names, timeout=900, refresh=False):
        """Introspect several classes in one launch."""
        lines = ['@introspect %s' % name for name in class_names]
        return self._cached('\n'.join(lines) + '\n', timeout, refresh=refresh).strip()

    def search(self, pattern, timeout=900, refresh=False):
        return self._cached('@search %s\n' % pattern, timeout, refresh=refresh).strip()

    def search_many(self, patterns, timeout=900, refresh=False):
        lines = ['@search %s' % pattern for pattern in patterns]
        return self._cached('\n'.join(lines) + '\n', timeout, refresh=refresh).strip()

    def call(self, expr, timeout=900):
        return self.run_script(expr + '\n', timeout=timeout).strip()

    def statements(self, lines, timeout=900):
        """Run a statement list; return the per-line responses."""
        text = self.run_script('\n'.join(lines) + '\n', timeout=timeout)
        return [line for line in text.splitlines() if line.strip()]
