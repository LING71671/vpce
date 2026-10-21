"""Geometry assignment. Pure arithmetic over a Spec.

A diagram whose shapes all sit at (0,0) renders as a pile, so boxes are placed
before anything is created. Strategy comes from the diagram profile unless the
spec overrides it:

    explicit  every node carries x/y
    grid      column-major packing
    layered   BFS levels along the edges
    usecase   actors in a left column, everything else in a grid to their right
    radial    first node in the middle, the rest on a ring
"""

from collections import deque

from . import profiles
from .spec import COL_GAP, DEFAULT_NODE_WIDTH, ROW_GAP

ACTOR_TYPES = ('Actor', 'Role')


def layout(spec):
    if not spec.layout.get('mode'):
        spec.layout['mode'] = profiles.for_diagram(spec.diagram)['layout']
    mode = spec.layout['mode']
    if mode == 'explicit':
        _explicit(spec)
    elif mode == 'usecase':
        _usecase(spec)
    elif mode == 'radial':
        _radial(spec)
    elif mode == 'layered':
        _layered(spec)
    else:
        _grid(spec)
    return spec


def _size(node):
    node.width = node.width or DEFAULT_NODE_WIDTH
    node.height = node.height or node.natural_height


def _origin(spec):
    return int(spec.layout.get('x', 40)), int(spec.layout.get('y', 40))


def _explicit(spec):
    x0, y0 = _origin(spec)
    cursor = x0
    for node in spec.nodes:
        _size(node)
        if node.x is None:
            node.x = cursor
            cursor += node.width + COL_GAP
        if node.y is None:
            node.y = y0


def _grid(spec):
    x0, y0 = _origin(spec)
    cols = int(spec.layout.get('columns') or 0) or max(1, int(len(spec.nodes) ** 0.5 + 0.99))
    for node in spec.nodes:
        _size(node)
    cell_w = max(n.width for n in spec.nodes) + COL_GAP
    heights = [0] * cols
    for index, node in enumerate(spec.nodes):
        col = index % cols
        node.x = x0 + col * cell_w
        node.y = y0 + heights[col]
        heights[col] += node.height + ROW_GAP


def _usecase(spec):
    """Actors left, use cases right of them."""
    x0, y0 = _origin(spec)
    for node in spec.nodes:
        _size(node)
    actors = [n for n in spec.nodes if n.type in ACTOR_TYPES]
    others = [n for n in spec.nodes if n.type not in ACTOR_TYPES]

    cursor = y0
    for node in actors:
        node.x = x0
        node.y = cursor
        cursor += node.height + ROW_GAP

    if not others:
        return
    left = x0 + (max((n.width for n in actors), default=0) + 2 * COL_GAP)
    cols = int(spec.layout.get('columns') or 0) or max(1, int(len(others) ** 0.5 + 0.99))
    cell_w = max(n.width for n in others) + COL_GAP
    heights = [0] * cols
    for index, node in enumerate(others):
        col = index % cols
        node.x = left + col * cell_w
        node.y = y0 + heights[col]
        heights[col] += node.height + ROW_GAP


def _radial(spec):
    import math
    x0, y0 = _origin(spec)
    for node in spec.nodes:
        _size(node)
    hub = spec.nodes[0]
    hub.x = x0
    hub.y = y0
    ring = spec.nodes[1:]
    if not ring:
        return
    radius = max(200, int(60 * len(ring) ** 0.5))
    step = 2 * math.pi / len(ring)
    for index, node in enumerate(ring):
        angle = -math.pi / 2 + index * step
        node.x = int(hub.x + 120 + radius * math.cos(angle))
        node.y = int(hub.y + radius * math.sin(angle) + radius)


def _layered(spec):
    x0, y0 = _origin(spec)
    for node in spec.nodes:
        _size(node)

    vertical = profiles.for_diagram(spec.diagram).get('direction') == 'vertical'
    outgoing = {node.id: [] for node in spec.nodes}
    incoming = {node.id: 0 for node in spec.nodes}
    for edge in spec.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target] += 1

    levels = {}
    queue = deque([n.id for n in spec.nodes if incoming[n.id] == 0])
    for node_id in queue:
        levels[node_id] = 0

    guard = len(spec.nodes) ** 2 + 1
    steps = 0
    while queue and steps < guard:
        steps += 1
        current = queue.popleft()
        for target in outgoing[current]:
            candidate = levels[current] + 1
            if levels.get(target, -1) < candidate:
                levels[target] = candidate
                queue.append(target)
    for node in spec.nodes:
        levels.setdefault(node.id, 0)

    columns = {}
    for node in spec.nodes:
        columns.setdefault(levels[node.id], []).append(node)

    if vertical:
        cell_h = max(n.height for n in spec.nodes) + ROW_GAP
        for level in sorted(columns):
            x = x0
            for node in columns[level]:
                node.x = x
                node.y = y0 + level * cell_h
                x += node.width + COL_GAP
    else:
        cell_w = max(n.width for n in spec.nodes) + COL_GAP
        for level in sorted(columns):
            y = y0
            for node in columns[level]:
                node.x = x0 + level * cell_w
                node.y = y
                y += node.height + ROW_GAP
    return spec
