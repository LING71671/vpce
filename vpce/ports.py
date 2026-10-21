"""Ports: the contracts the service layer depends on.

Adapters implement these; the service never learns whether a project is read
through XML export, memory, or a mocked fixture.
"""

try:  # 3.8+
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    Protocol = object

    def runtime_checkable(cls):
        return cls


@runtime_checkable
class Runtime(Protocol):
    """Runs one Visual Paradigm command class and returns its console output."""

    def run(self, command, args, timeout=600, headless=True, check=True):
        ...

    def describe(self):
        ...


@runtime_checkable
class ProjectIO(Protocol):
    """Reads and writes one .vpp file."""

    project_path: str

    def export_xml(self, force=False, out_dir=None):
        """Return a path to the project's XML representation."""

    def model(self, refresh=False):
        """Return a `core.model.ProjectModel`."""

    def import_xml(self, xml_path, match_by_name=True, backup=True):
        """Merge an XML document; return the backup path."""

    def render(self, diagrams='*', out='.', fmt='png', timeout=900):
        """Render diagrams; return [{'file', 'name', 'bytes'}]."""

    def backup(self):
        """Copy the project next to itself; return the new path."""


@runtime_checkable
class Api(Protocol):
    """Evaluates Open API statements inside a headless VP process."""

    def run_script(self, script, timeout=900):
        ...

    def introspect(self, class_name, timeout=900):
        ...

    def search(self, pattern, timeout=900):
        ...
