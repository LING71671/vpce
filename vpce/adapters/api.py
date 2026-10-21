"""Open API adapter: ships statements to the `com.vpce.bridge` plugin.

Implements `ports.Api`. The bridge itself is built from `java/bridge` and has
to be installed once into the Visual Paradigm plugin directory; everything
below that is transport detail.
"""

import base64
import os
import shutil

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


class OpenApi(object):
    def __init__(self, runtime, project_path):
        self.runtime = runtime
        self.project_path = project_path

    def run_script(self, script, timeout=900):
        if not script.endswith('\n'):
            script += '\n'
        blob = base64.b64encode(script.encode('utf-8')).decode('ascii')
        result = self.runtime.run('Plugin', ['-project', self.project_path,
                                             '-pluginid', PLUGIN_ID,
                                             '-pluginargs', blob],
                                  timeout=timeout, check=False)
        output = result.output or ''
        for line in output.splitlines():
            if line.startswith(MARKER):
                return base64.b64decode(line[len(MARKER):].strip()).decode('utf-8', 'replace')
        if 'Plugin not found' in output:
            raise VpceError('bridge plugin not installed; run: vpce bridge --install')
        if 'ClassNotFoundException' in output:
            raise ConfigurationError('bridge class failed to load; check '
                                     'plugin.xml + lib/bridge.jar layout')
        raise CommandFailure('Plugin(bridge)', result.returncode, output)

    def introspect(self, class_name, timeout=900):
        return self.run_script('@introspect %s\n' % class_name, timeout=timeout).strip()

    def search(self, pattern, timeout=900):
        return self.run_script('@search %s\n' % pattern, timeout=timeout).strip()

    def call(self, expr, timeout=900):
        return self.run_script(expr + '\n', timeout=timeout).strip()

    def statements(self, lines, timeout=900):
        """Run a statement list; return the per-line responses."""
        text = self.run_script('\n'.join(lines) + '\n', timeout=timeout)
        return [line for line in text.splitlines() if line.strip()]
