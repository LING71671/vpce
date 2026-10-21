"""Project adapter: one .vpp file, read through ExportXML, written through ImportXML.

Implements `ports.ProjectIO`. Nothing here knows about drawing specs.
"""

import hashlib
import os
import shutil
import tempfile
import time

from ..core.errors import UpgradeRequired, VpceError
from ..core.model import ProjectModel

XML_ENTRY = 'project.xml'


def safe_name(name):
    keep = ''.join(c if (c.isalnum() or c in ' -_.') else '_' for c in name)
    return '_'.join(keep.split()) or 'diagram'


class XmlProject(object):
    def __init__(self, project_path, runtime, cache_root=None):
        self.runtime = runtime
        self.project_path = os.path.abspath(project_path)
        if not os.path.isfile(self.project_path):
            raise VpceError('project not found: %s' % self.project_path)
        self.cache_root = cache_root or os.path.join(tempfile.gettempdir(), 'vpce-cache')
        self._model = None
        self._cache_key = None

    # -- cache -------------------------------------------------------------

    def _stat_key(self):
        stat = os.stat(self.project_path)
        return (stat.st_mtime_ns, stat.st_size)

    @property
    def cache_dir(self):
        tag = hashlib.sha1(self.project_path.lower().encode('utf-8')).hexdigest()[:12]
        return os.path.join(self.cache_root, tag)

    def invalidate(self):
        self._model = None
        self._cache_key = None

    # -- read --------------------------------------------------------------

    def export_xml(self, force=False, out_dir=None):
        out_dir = out_dir or self.cache_dir
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, XML_ENTRY)
        if not force and os.path.isfile(path) and self._cache_key == self._stat_key():
            return path
        try:
            self.runtime.run('ExportXML', ['-project', self.project_path,
                                           '-out', out_dir, '-simple'])
        except UpgradeRequired:
            self.runtime.run('ExportXML', ['-project', self.project_path, '-upgrade-project',
                                           '-out', out_dir, '-simple'])
            self.invalidate()
        self._cache_key = self._stat_key()
        return path

    def model(self, refresh=False):
        if refresh or self._model is None:
            self._model = ProjectModel.load(self.export_xml(force=refresh))
        return self._model

    def summary(self, refresh=False):
        return self.model(refresh=refresh).summary()

    def find(self, type=None, name=None, refresh=False):
        return [e.to_dict() for e in self.model(refresh=refresh).elements(type=type, name=name)]

    def diagrams(self, refresh=False):
        return [d.to_dict() for d in self.model(refresh=refresh).diagrams]

    # -- write -------------------------------------------------------------

    def backup(self):
        stamp = time.strftime('%Y%m%d-%H%M%S')
        target = '%s.bak-%s' % (self.project_path, stamp)
        shutil.copy2(self.project_path, target)
        return target

    def import_xml(self, xml_path, match_by_name=True, backup=True):
        bak = self.backup() if backup else None
        args = ['-project', self.project_path, '-file', os.path.abspath(xml_path)]
        if match_by_name:
            args.append('-matchByName')
        try:
            self.runtime.run('ImportXML', args)
        except UpgradeRequired:
            args.insert(2, '-upgrade-project')
            self.runtime.run('ImportXML', args)
        self.invalidate()
        return bak

    def import_document(self, text, match_by_name=True, backup=True):
        fd, path = tempfile.mkstemp(suffix='.xml', prefix='vpce-import-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(text)
            return self.import_xml(path, match_by_name=match_by_name, backup=backup)
        finally:
            _unlink(path)

    def verify_named(self, names, diagrams=()):
        """Re-read the project and report which names landed."""
        model = self.model(refresh=True)
        present = {e.name for e in model.elements()}
        diagram_names = {d.name for d in model.diagrams}
        found = [n for n in names if n in present]
        missing = [n for n in names if n not in present]
        found_diagrams = [n for n in diagrams if n in diagram_names]
        missing_diagrams = [n for n in diagrams if n not in diagram_names]
        return {'elements_found': found, 'elements_missing': missing,
                'diagrams_found': found_diagrams, 'diagrams_missing': missing_diagrams}

    # -- images ------------------------------------------------------------

    def render(self, diagrams='*', out='.', fmt='png', timeout=900):
        out_dir = os.path.abspath(out)
        if isinstance(diagrams, (list, tuple)):
            names = [n for n in diagrams if n]
        elif diagrams and diagrams != '*':
            names = [n.strip() for n in str(diagrams).split(',') if n.strip()]
        else:
            names = [d.name for d in self.model().diagrams]
        if not names:
            raise VpceError('project has no diagrams')
        os.makedirs(out_dir, exist_ok=True)

        listfile = None
        if len(names) == 1:
            target = os.path.join(out_dir, '%s.%s' % (safe_name(names[0]), fmt))
            diagram_arg = names[0]
            expected = [target]
        else:
            fd, listfile = tempfile.mkstemp(suffix='.txt', prefix='vpce-diagrams-')
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(names) + '\n')
            target = out_dir
            diagram_arg = '@' + listfile
            expected = [os.path.join(out_dir, '%s.%s' % (n, fmt)) for n in names]
        try:
            self.runtime.run('ExportDiagramImage',
                             ['-project', self.project_path, '-out', target,
                              '-diagram', diagram_arg, '-type', fmt], timeout=timeout)
        finally:
            if listfile:
                _unlink(listfile)

        produced = []
        for path in expected:
            if os.path.isfile(path):
                produced.append({'file': path, 'name': os.path.basename(path),
                                 'bytes': os.path.getsize(path)})
        return produced

    def upgrade(self):
        bak = self.backup()
        try:
            self.runtime.run('ExportXML', ['-project', self.project_path, '-upgrade-project',
                                           '-out', self.cache_dir, '-simple'])
        finally:
            self.invalidate()
        return bak


def _unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass
