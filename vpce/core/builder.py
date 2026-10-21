"""Build an ImportXML document. Pure string building.

Used by the XML channel, which needs no plugin at all -- the fallback when the
Open API bridge cannot be installed.
"""

import io
import random
import string
import xml.etree.ElementTree as ET

ID_ALPHABET = string.ascii_letters + string.digits + '_-'


def new_id(prefix='mcp'):
    body = ''.join(random.choice(ID_ALPHABET) for _ in range(16 - len(prefix)))
    return prefix + body


class ImportBuilder(object):
    DEFAULTS = {
        'ConnectToCodeModel': '1',
        'QualityScore': '-1',
        'Root': 'false',
        'Leaf': 'false',
        'Abstract': 'false',
        'Visibility': 'public',
    }

    SHAPE_DEFAULTS = {
        'Background': 'rgb(122, 207, 245)',
        'Foreground': 'rgb(0, 0, 0)',
        'ConnectToPoint': 'true',
        'ConnectionPointType': '2',
        'CoverConnector': 'false',
        'Selectable': 'true',
        'ShowAttributeType': '1',
        'ShowOperationSignature': 'true',
        'VisibilityStyle': '1',
        'PresentationOption': '4',
        'PrimitiveShapeType': '0',
        'ZOrder': '0',
    }

    def __init__(self, name='mcp', uml_version='2.x', author='vpce'):
        self.name = name
        self.uml_version = uml_version
        self.author = author
        self.models = ET.Element('Models')
        self.diagrams = ET.Element('Diagrams')
        self._created = []

    # -- model side --------------------------------------------------------

    def add_element(self, type, name, element_id=None, parent=None, **attrs):
        element_id = element_id or new_id()
        node = ET.SubElement(parent if parent is not None else self.models, type)
        data = dict(self.DEFAULTS)
        data.update(attrs)
        node.set('Id', element_id)
        node.set('Name', name)
        for key, value in data.items():
            if value is not None:
                node.set(key, str(value))
        self._created.append({'type': type, 'name': name, 'id': element_id})
        return element_id

    def add_class(self, name, element_id=None, attributes=(), **attrs):
        class_id = self.add_element('Class', name, element_id, **attrs)
        if attributes:
            parent = self.models.find(".//*[@Id='%s']" % class_id)
            if parent is not None:
                children = ET.SubElement(parent, 'ModelChildren')
                for attr_name, attr_type in attributes:
                    self.add_element('Attribute', attr_name, parent=children,
                                     Type=attr_type or '')
        return class_id

    # -- diagram side ------------------------------------------------------

    def add_diagram(self, diagram_type, name, shapes=(), element_id=None, **attrs):
        element_id = element_id or new_id('d')
        node = ET.SubElement(self.diagrams, diagram_type)
        node.set('Id', element_id)
        node.set('Name', name)
        node.set('DiagramBackground', 'rgb(255, 255, 255)')
        node.set('AlignToGrid', 'false')
        node.set('AutoFitShapesSize', 'false')
        node.set('ZoomRatio', '1.0')
        for key, value in attrs.items():
            node.set(key, str(value))
        container = ET.SubElement(node, 'Shapes')
        default_shape = diagram_type[:-7] if diagram_type.endswith('Diagram') else 'Shape'
        for index, spec in enumerate(shapes):
            self._add_shape(container, default_shape, spec, index)
        self._created.append({'type': diagram_type, 'name': name, 'id': element_id})
        return element_id

    def _add_shape(self, container, default_type, spec, index):
        kind = spec.get('type') or default_type
        shape = ET.SubElement(container, kind)
        x = int(spec.get('x', 40 + 200 * index))
        y = int(spec.get('y', 40))
        width = int(spec.get('width', 140))
        height = int(spec.get('height', 80))
        name = spec.get('name', '')
        shape.set('Id', new_id('s'))
        shape.set('Name', name)
        shape.set('Model', spec['model_id'])
        shape.set('MetaModelElement', spec['model_id'])
        shape.set('X', str(x))
        shape.set('Y', str(y))
        shape.set('Width', str(width))
        shape.set('Height', str(height))
        for key, value in self.SHAPE_DEFAULTS.items():
            shape.set(key, value)
        font = ET.SubElement(shape, 'ElementFont')
        font.set('Color', 'rgb(0, 0, 0)')
        font.set('Name', 'Dialog')
        font.set('Size', '11')
        font.set('Style', '0')
        fill = ET.SubElement(shape, 'FillColor')
        fill.set('Color', 'rgb(122, 207, 245)')
        fill.set('Style', '1')
        fill.set('Transparency', '0')
        fill.set('Type', '1')
        cap = ET.SubElement(shape, 'Caption')
        cap.set('Height', '16')
        cap.set('InternalHeight', '-2147483648')
        cap.set('InternalWidth', '-2147483648')
        cap.set('Side', 'North')
        cap.set('Visible', 'true')
        cap.set('Width', str(max(40, width - 8)))
        cap.set('X', str(x + 4))
        cap.set('Y', str(y + 2))
        ET.SubElement(shape, 'CompartmentFont').set('Value', 'none')
        return shape

    # -- output ------------------------------------------------------------

    def render(self):
        root = ET.Element('Project')
        root.set('Name', self.name)
        root.set('UmlVersion', self.uml_version)
        root.set('Xml_structure', 'simple')
        root.set('Author', self.author)
        root.append(self.models)
        if len(self.diagrams):
            root.append(self.diagrams)
        try:
            ET.indent(root, space='\t')
        except AttributeError:
            pass
        buffer = io.BytesIO()
        ET.ElementTree(root).write(buffer, encoding='utf-8', xml_declaration=True)
        return buffer.getvalue().decode('utf-8')

    def rendered_elements(self):
        return list(self._created)
