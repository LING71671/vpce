"""Use cases. Depends on ports only; knows nothing about argparse or MCP."""

import os
import re

from .core import layout as layout_mod
from .core.builder import ImportBuilder
from .core.errors import SpecError, VpceError
from .core.program import to_statements

_ID_LINE = re.compile(r'=\s*String\s+(\S+)\s*$')


class ProjectService(object):
    """Read/write one project through the XML channel."""

    def __init__(self, project):
        self.project = project

    def summary(self, refresh=False):
        return self.project.summary(refresh=refresh)

    def elements(self, type=None, name=None, refresh=False):
        return self.project.find(type=type, name=name, refresh=refresh)

    def diagrams(self, refresh=False):
        return self.project.diagrams(refresh=refresh)

    def export_xml(self, out_dir=None):
        path = self.project.export_xml(force=True, out_dir=out_dir)
        return {'xml': path, 'bytes': os.path.getsize(path)}

    def render(self, diagrams='*', out='.', fmt='png'):
        files = self.project.render(diagrams=diagrams, out=out, fmt=fmt)
        return {'out': os.path.abspath(out), 'files': files}

    def import_document(self, text, match_by_name=True):
        backup = self.project.import_document(text, match_by_name=match_by_name)
        return {'backup': backup, 'summary': self.project.summary(refresh=True)}

    def import_file(self, path, match_by_name=True):
        backup = self.project.import_xml(path, match_by_name=match_by_name)
        return {'backup': backup, 'summary': self.project.summary(refresh=True)}

    def upgrade(self):
        return {'backup': self.project.upgrade(),
                'summary': self.project.summary(refresh=True)}

    def create_class(self, name, attributes=(), diagram=None):
        builder = ImportBuilder(name=self.project.model().name or 'vpce')
        class_id = builder.add_class(name, attributes=attributes)
        if diagram:
            builder.add_diagram('ClassDiagram', diagram, shapes=[{
                'model_id': class_id, 'type': 'Class', 'name': name,
                'x': 60, 'y': 60, 'width': 160, 'height': 90}])
        backup = self.project.import_document(builder.render(), match_by_name=True)
        report = self.project.verify_named([name], [diagram] if diagram else [])
        report['backup'] = backup
        report['missing'] = report['elements_missing'] + report['diagrams_missing']
        return report


class DrawService(object):
    """Turn a drawing spec into real model elements, diagrams and images."""

    def __init__(self, project, api):
        self.project = project
        self.api = api

    def draw(self, spec, out=None, fmt='png', verify=True):
        layout_mod.layout(spec)
        statements, _ = to_statements(spec)
        response = self.api.run_script('\n'.join(statements) + '\n')
        errors = [line for line in response.splitlines() if line.startswith('error#')]
        if errors:
            raise VpceError('draw failed: %s' % '; '.join(errors[:4]))

        diagram_id = None
        for line in reversed(response.splitlines()):
            match = _ID_LINE.search(line)
            if match:
                diagram_id = match.group(1)
                break

        result = {
            'diagram': spec.describe(),
            'diagram_id': diagram_id,
            'statements': len(statements),
            'script': '\n'.join(statements),
        }
        if verify:
            result['verify'] = self.project.verify_named(
                [node.name for node in spec.nodes], [spec.name])
        if out:
            result['images'] = self.project.render(diagrams=spec.name, out=out, fmt=fmt)
        return result

    def plan(self, spec):
        """Same input, no side effects: layout + script, for inspection."""
        layout_mod.layout(spec)
        statements, _ = to_statements(spec)
        return {'diagram': spec.describe(), 'script': '\n'.join(statements)}


class ApiService(object):
    def __init__(self, api):
        self.api = api

    def run(self, script):
        return self.api.run_script(script)

    def introspect(self, class_name, refresh=False):
        """One class, or several in a single launch."""
        if isinstance(class_name, (list, tuple)):
            return self.api.introspect_many(class_name, refresh=refresh)
        return self.api.introspect(class_name, refresh=refresh)

    def search(self, pattern, refresh=False):
        if isinstance(pattern, (list, tuple)):
            return self.api.search_many(pattern, refresh=refresh)
        return self.api.search(pattern, refresh=refresh)
