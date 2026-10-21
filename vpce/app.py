"""Composition root: the one place that wires adapters to services.

Transports (CLI, MCP) construct an App and call service methods; they never
see a runtime, a port or a file handle.
"""

import os

from .adapters.api import OpenApi
from .adapters.runtime import VpRuntime
from .adapters.workspace import XmlProject
from .core.spec import Spec
from .service import ApiService, DrawService, ProjectService


class App(object):
    def __init__(self, vp_home=None, project=None):
        self.vp_home = vp_home
        self.project_path = os.path.abspath(project) if project else None
        self._runtime = None
        self._project = None

    # -- lazily built pieces ----------------------------------------------

    @property
    def runtime(self):
        if self._runtime is None:
            self._runtime = VpRuntime(self.vp_home)
        return self._runtime

    def require_project(self):
        if not self.project_path:
            raise ValueError('this operation needs a project path')
        return self.project_path

    @property
    def project(self):
        if self._project is None:
            self._project = XmlProject(self.require_project(), self.runtime)
        return self._project

    def bind(self, project):
        """Point the app at another project file."""
        self.project_path = os.path.abspath(project)
        self._project = None
        return self

    # -- services ----------------------------------------------------------

    def projects(self):
        return ProjectService(self.project)

    def drawing(self):
        return DrawService(self.project, OpenApi(self.runtime, self.require_project()))

    def apis(self):
        return ApiService(OpenApi(self.runtime, self.require_project()))

    def draw(self, spec, out=None, fmt='png', plan_only=False):
        spec = spec if isinstance(spec, Spec) else Spec.load(spec)
        service = self.drawing()
        return service.plan(spec) if plan_only else service.draw(spec, out=out, fmt=fmt)

    def install_bridge(self, force=False):
        from .adapters import api as api_adapter
        return api_adapter.install(force=force)

    def uninstall_bridge(self):
        from .adapters import api as api_adapter
        return api_adapter.uninstall()

    def bridge_status(self):
        from .adapters import api as api_adapter
        info = {'installed': api_adapter.is_installed(),
                'plugin_root': api_adapter.plugin_root(),
                'build': api_adapter.BUILT_PLUGIN}
        if self.project_path:
            try:
                info['probe'] = self.apis().run('ApplicationManager.instance()').strip()
            except Exception as exc:
                info['probe_error'] = str(exc)
        return info
