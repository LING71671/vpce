"""Diagram specification: the thing an AI writes instead of clicking.

A spec is data only -- no IO, no subprocess, no Visual Paradigm types. It maps
1:1 onto the Open API operations the adapter knows how to perform:

    node  -> IModelElementFactory.create(type) + createChild(...) + shape bounds
    edge  -> IModelElementFactory.create(type) + setFrom/setTo + createConnector

Because both the element type and the diagram type are plain strings, one spec
format covers every diagram Visual Paradigm can open (107 type constants).

JSON shape::

    {
      "diagram": "ClassDiagram",
      "name": "Order System",
      "nodes": [
        {"id": "customer", "type": "Class", "name": "Customer",
         "attributes": ["id:long", "name:string"],
         "operations": ["placeOrder"]},
        {"id": "order", "type": "Class", "name": "Order"}
      ],
      "edges": [
        {"from": "customer", "to": "order", "type": "Association", "name": "places"}
      ],
      "layout": {"mode": "layered", "x": 40, "y": 40}
    }
"""

import difflib
import json
import os
import re

from . import profiles
from .errors import SpecError

_CATALOG = None


def type_catalog():
    """Every model type string IModelElementFactory accepts (1455 of them)."""
    global _CATALOG
    if _CATALOG is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_types.json')
        with open(path, encoding='utf-8') as fh:
            _CATALOG = json.load(fh)
    return _CATALOG


def suggest_type(name):
    return difflib.get_close_matches(name, list(type_catalog()), n=3, cutoff=0.55)

DEFAULT_NODE_WIDTH = 170
DEFAULT_NODE_HEIGHT = 80
ROW_GAP = 70
COL_GAP = 70

_ID_RE = re.compile(r'^[A-Za-z_][\w.-]*$')


class Node(object):
    __slots__ = ('id', 'type', 'name', 'attributes', 'operations',
                 'x', 'y', 'width', 'height', 'stereotype')

    def __init__(self, id, type='Class', name=None, attributes=(), operations=(),
                 x=None, y=None, width=None, height=None, stereotype=None):
        self.id = id
        self.type = type
        self.name = name if name is not None else id
        self.attributes = list(attributes)
        self.operations = list(operations)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.stereotype = stereotype

    @property
    def natural_height(self):
        rows = len(self.attributes) + len(self.operations)
        return max(DEFAULT_NODE_HEIGHT, 44 + 17 * rows)

    @classmethod
    def from_dict(cls, raw, index, default_type='Class'):
        if not isinstance(raw, dict):
            raise SpecError('nodes[%d] must be an object' % index)
        node_id = raw.get('id') or raw.get('name')
        if not node_id:
            raise SpecError('nodes[%d] needs an id' % index)
        if not _ID_RE.match(str(node_id)):
            raise SpecError('invalid node id %r (letters, digits, _ . - only)' % node_id)
        return cls(
            id=str(node_id),
            type=raw.get('type') or default_type,
            name=raw.get('name'),
            attributes=raw.get('attributes') or (),
            operations=raw.get('operations') or (),
            x=raw.get('x'), y=raw.get('y'),
            width=raw.get('width'), height=raw.get('height'),
            stereotype=raw.get('stereotype'),
        )

    def attribute_pairs(self):
        out = []
        for item in self.attributes:
            if isinstance(item, dict):
                out.append((str(item.get('name', '')), str(item.get('type', ''))))
            else:
                name, _, typ = str(item).partition(':')
                out.append((name.strip(), typ.strip()))
        return [pair for pair in out if pair[0]]

    def operation_names(self):
        out = []
        for item in self.operations:
            if isinstance(item, dict):
                out.append(str(item.get('name', '')))
            else:
                out.append(str(item).split('(')[0].strip())
        return [n for n in out if n]


class Edge(object):
    __slots__ = ('source', 'target', 'type', 'name', 'from_role', 'to_role')

    def __init__(self, source, target, type='Association', name='',
                 from_role='', to_role=''):
        self.source = source
        self.target = target
        self.type = type
        self.name = name
        self.from_role = from_role
        self.to_role = to_role

    @classmethod
    def from_dict(cls, raw, index):
        if not isinstance(raw, dict):
            raise SpecError('edges[%d] must be an object' % index)
        source = raw.get('from') or raw.get('source')
        target = raw.get('to') or raw.get('target')
        if not source or not target:
            raise SpecError('edges[%d] needs "from" and "to"' % index)
        return cls(str(source), str(target),
                   type=raw.get('type') or 'Association',
                   name=raw.get('name') or '',
                   from_role=raw.get('from_role') or raw.get('fromRole') or '',
                   to_role=raw.get('to_role') or raw.get('toRole') or '')


class Spec(object):
    def __init__(self, diagram='ClassDiagram', name='Diagram', nodes=(), edges=(),
                 layout=None, strict=True):
        self.diagram = diagram
        self.name = name
        self.nodes = list(nodes)
        self.edges = list(edges)
        self.layout = dict(layout or {})
        self.strict = strict

    # -- construction ------------------------------------------------------

    @classmethod
    def from_dict(cls, raw):
        if not isinstance(raw, dict):
            raise SpecError('spec must be a JSON object')
        diagram = raw.get('diagram') or raw.get('diagram_type') or 'ClassDiagram'
        name = raw.get('name') or 'Diagram'
        default_type = profiles.for_diagram(diagram)['node_type']
        nodes = [Node.from_dict(item, i, default_type)
                 for i, item in enumerate(raw.get('nodes') or [])]
        if not nodes:
            raise SpecError('spec has no nodes')
        edges = [Edge.from_dict(item, i) for i, item in enumerate(raw.get('edges') or [])]
        spec = cls(diagram=diagram, name=name, nodes=nodes, edges=edges,
                   layout=raw.get('layout'), strict=raw.get('strict', True))
        spec.validate()
        return spec

    @classmethod
    def load(cls, path):
        with open(path, encoding='utf-8') as fh:
            try:
                raw = json.load(fh)
            except ValueError as exc:
                raise SpecError('%s is not valid JSON: %s' % (path, exc))
        return cls.from_dict(raw)

    def validate(self, strict=True):
        seen = set()
        for node in self.nodes:
            if node.id in seen:
                raise SpecError('duplicate node id %r' % node.id)
            seen.add(node.id)
        for edge in self.edges:
            for end in (edge.source, edge.target):
                if end not in seen:
                    raise SpecError('edge endpoint %r is not a node id' % end)
            if edge.source == edge.target:
                raise SpecError('self-loop on %r is not supported yet' % edge.source)
        if strict and self.strict:
            catalog = type_catalog()
            for item in [n.type for n in self.nodes] + [e.type for e in self.edges]:
                if item not in catalog:
                    hint = suggest_type(item)
                    raise SpecError(
                        'unknown element type %r%s' % (
                            item, ('; did you mean %s?' % ', '.join(hint)) if hint else ''))
        return self

    # -- queries -----------------------------------------------------------

    def node(self, node_id):
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise SpecError('unknown node %r' % node_id)

    def describe(self):
        types = {}
        for node in self.nodes:
            types[node.type] = types.get(node.type, 0) + 1
        edge_types = {}
        for edge in self.edges:
            edge_types[edge.type] = edge_types.get(edge.type, 0) + 1
        return {
            'diagram': self.diagram,
            'name': self.name,
            'nodes': len(self.nodes),
            'edges': len(self.edges),
            'node_types': types,
            'edge_types': edge_types,
        }
