"""Read-only view over Visual Paradigm's "simple" project XML.

Pure: takes a path, returns data. No subprocess, no caching policy -- the
adapter decides when to refresh.
"""

import collections
import xml.etree.ElementTree as ET


class Element(object):
    __slots__ = ('type', 'id', 'name', 'attrib', 'parent', 'children')

    def __init__(self, node, parent=None):
        self.type = node.tag
        self.attrib = dict(node.attrib)
        self.id = self.attrib.get('Id') or self.attrib.get('id')
        self.name = self.attrib.get('Name') or self.attrib.get('name') or ''
        self.parent = parent
        self.children = []

    @property
    def path(self):
        parts, cur = [], self
        while cur is not None:
            if cur.name:
                parts.append(cur.name)
            cur = cur.parent
        return '/'.join(reversed(parts))

    def walk(self):
        yield self
        for child in self.children:
            for item in child.walk():
                yield item

    def to_dict(self, depth=0):
        data = {'type': self.type, 'id': self.id, 'name': self.name}
        if self.attrib.get('Documentation_plain'):
            data['documentation'] = self.attrib['Documentation_plain']
        if self.children and depth < 2:
            data['children'] = [c.to_dict(depth + 1) for c in self.children]
        return data

    def __repr__(self):
        return '<%s %r %s>' % (self.type, self.name, self.id)


class Diagram(object):
    __slots__ = ('type', 'id', 'name', 'attrib', 'shapes', 'connectors')

    def __init__(self, node):
        self.type = node.tag
        self.attrib = dict(node.attrib)
        self.id = self.attrib.get('Id')
        self.name = self.attrib.get('Name') or ''
        shapes = node.find('Shapes')
        connectors = node.find('Connectors')
        self.shapes = list(shapes) if shapes is not None else []
        self.connectors = list(connectors) if connectors is not None else []

    def to_dict(self):
        kinds = collections.Counter(shape.tag for shape in self.shapes)
        return {
            'type': self.type,
            'id': self.id,
            'name': self.name,
            'shapes': len(self.shapes),
            'connectors': len(self.connectors),
            'shape_types': dict(kinds),
        }

    def __repr__(self):
        return '<%s %r shapes=%d>' % (self.type, self.name, len(self.shapes))


class ProjectModel(object):
    def __init__(self, root, source=None):
        self.root = root
        self.source = source
        self.name = root.get('Name') or ''
        self.uml_version = root.get('UmlVersion') or ''
        self.roots = []
        self.diagrams = []
        models = root.find('Models')
        if models is not None:
            for node in models:
                if node.tag == 'ProjectFormat':
                    continue
                self.roots.append(self._parse(node, None))
        container = root.find('Diagrams')
        if container is not None:
            for node in container:
                self.diagrams.append(Diagram(node))

    def _parse(self, node, parent):
        element = Element(node, parent)
        children = node.find('ModelChildren')
        if children is not None:
            for child in children:
                element.children.append(self._parse(child, element))
        return element

    @classmethod
    def load(cls, path):
        return cls(ET.parse(path).getroot(), source=path)

    # -- queries -----------------------------------------------------------

    def elements(self, type=None, name=None):
        out = []
        for root in self.roots:
            for element in root.walk():
                if type and element.type != type:
                    continue
                if name and element.name != name:
                    continue
                out.append(element)
        return out

    def diagrams_of(self, type=None):
        return [d for d in self.diagrams if not type or d.type == type]

    def summary(self):
        counts = collections.Counter(el.type for el in self.elements())
        return {
            'project': self.name,
            'uml_version': self.uml_version,
            'model_elements': sum(counts.values()),
            'types': dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            'diagrams': [d.to_dict() for d in self.diagrams],
        }
