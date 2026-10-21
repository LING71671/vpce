"""Translate a Spec into bridge statements. Pure string building.

This is the only place that knows the shape of the Open API recipe; the
adapter just ships the resulting lines to the plugin and reads the answers.

Verified recipe (CE 18.1):

    createDiagram(type)                     -> IDiagramUIModel
    IModelElementFactory.create(type)       -> element of any UML type
    element.createChild("Attribute")        -> member (VP adds the parentheses)
    createDiagramElement(diagram, element)  -> shape, and attaches the element
                                               to the project root
    shape.setBounds(...)                    -> geometry is *not* optional
    shape.setRequestResetCaption(true)      -> draws the name caption
    createConnector(diagram, rel, s1, s2, null)
    saveProject()
"""


def _q(text):
    return '"%s"' % str(text).replace('\\', '\\\\').replace('"', '\\"')


def to_statements(spec):
    """Return (statements, var_index) where var_index maps node id -> $var."""
    lines = [
        '$am = ApplicationManager.instance()',
        '$dm = $am.getDiagramManager()',
        '$f = IModelElementFactory.instance()',
        '$d = $dm.createDiagram(%s)' % _q(spec.diagram),
        '$d.setName(%s)' % _q(spec.name),
    ]

    shape_var = {}
    for index, node in enumerate(spec.nodes):
        var = '$n%d' % index
        shape_var[node.id] = '$s%d' % index
        lines.append('%s = $f.create(%s)' % (var, _q(node.type)))
        lines.append('%s.setName(%s)' % (var, _q(node.name)))
        if node.stereotype:
            lines.append('%s.addStereotype(%s)' % (var, _q(node.stereotype)))
        for child_index, (name, type_name) in enumerate(node.attribute_pairs()):
            child = '$a%d_%d' % (index, child_index)
            lines.append('%s = %s.createChild("Attribute")' % (child, var))
            lines.append('%s.setName(%s)' % (child, _q(name)))
            if type_name:
                lines.append('%s.setType(%s)' % (child, _q(type_name)))
        for child_index, name in enumerate(node.operation_names()):
            child = '$o%d_%d' % (index, child_index)
            lines.append('%s = %s.createChild("Operation")' % (child, var))
            lines.append('%s.setName(%s)' % (child, _q(name)))

        shape = shape_var[node.id]
        lines.append('%s = $dm.createDiagramElement($d, %s)' % (shape, var))
        lines.append('%s.setBounds(%d, %d, %d, %d)'
                     % (shape, int(node.x), int(node.y), int(node.width), int(node.height)))
        lines.append('%s.setRequestResetCaption(true)' % shape)

    for index, edge in enumerate(spec.edges):
        rel = '$r%d' % index
        lines.append('%s = $f.create(%s)' % (rel, _q(edge.type)))
        if edge.name:
            lines.append('%s.setName(%s)' % (rel, _q(edge.name)))
        lines.append('%s.setFrom($n%d)' % (rel, _index_of(spec, edge.source)))
        lines.append('%s.setTo($n%d)' % (rel, _index_of(spec, edge.target)))
        lines.append('$dm.createConnector($d, %s, %s, %s, null)'
                     % (rel, shape_var[edge.source], shape_var[edge.target]))

    lines.append('$am.getProjectManager().saveProject()')
    lines.append('$d.getId()')
    return lines, shape_var


def _index_of(spec, node_id):
    for index, node in enumerate(spec.nodes):
        if node.id == node_id:
            return index
    raise KeyError(node_id)


def render_text(spec, shape_var=None):
    """The script as a single string, for logging or --dry-run."""
    lines, _ = to_statements(spec)
    return '\n'.join(lines) + '\n'
