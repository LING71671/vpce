"""Unit tests for the pure core. No Visual Paradigm installation needed.

    python -m unittest discover -s tests -p "test_core.py"

Covers spec parsing and validation, layout, statement generation, the XML
model reader and the XML import builder.
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.core import layout, profiles  # noqa: E402
from vpce.core.builder import ImportBuilder  # noqa: E402
from vpce.core.errors import SpecError  # noqa: E402
from vpce.core.model import ProjectModel  # noqa: E402
from vpce.core.program import to_statements  # noqa: E402
from vpce.core.spec import Spec, type_catalog  # noqa: E402

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Project Name="Demo" UmlVersion="2.x" Xml_structure="simple">
  <Models>
    <Package Id="pkg1" Name="Domain">
      <ModelChildren>
        <Class Id="cls1" Name="Order">
          <ModelChildren>
            <Attribute Id="at1" Name="total"/>
          </ModelChildren>
        </Class>
      </ModelChildren>
    </Package>
    <ModelRelationshipContainer Id="rel1" Name="relationships">
      <ModelChildren>
        <Association Id="asc1" Name="places"/>
      </ModelChildren>
    </ModelRelationshipContainer>
  </Models>
  <Diagrams>
    <ClassDiagram Id="d1" Name="Class Diagram">
      <Shapes>
        <Class Id="s1" Name="Order" Model="cls1"/>
      </Shapes>
      <Connectors/>
    </ClassDiagram>
  </Diagrams>
</Project>
"""


def spec_dict(**overrides):
    data = {
        'diagram': 'ClassDiagram',
        'name': 'Order System',
        'nodes': [
            {'id': 'customer', 'type': 'Class', 'name': 'Customer',
             'attributes': ['id:long'], 'operations': ['placeOrder']},
            {'id': 'order', 'type': 'Class', 'name': 'Order'},
        ],
        'edges': [{'from': 'customer', 'to': 'order', 'type': 'Association'}],
    }
    data.update(overrides)
    return data


class SpecTest(unittest.TestCase):
    def test_parses_nodes_and_edges(self):
        spec = Spec.from_dict(spec_dict())
        self.assertEqual(len(spec.nodes), 2)
        self.assertEqual(spec.nodes[0].attribute_pairs(), [('id', 'long')])
        self.assertEqual(spec.nodes[0].operation_names(), ['placeOrder'])
        self.assertEqual(spec.describe()['node_types'], {'Class': 2})

    def test_default_node_type_follows_diagram_profile(self):
        spec = Spec.from_dict({
            'diagram': 'UseCaseDiagram', 'name': 'U',
            'nodes': [{'id': 'a', 'name': 'Actor A'}],
        })
        self.assertEqual(spec.nodes[0].type, 'UseCase')

    def test_duplicate_id_rejected(self):
        with self.assertRaises(SpecError):
            Spec.from_dict(spec_dict(nodes=[{'id': 'a'}, {'id': 'a'}]))

    def test_unknown_endpoint_rejected(self):
        with self.assertRaises(SpecError):
            Spec.from_dict(spec_dict(edges=[{'from': 'a', 'to': 'ghost'}]))

    def test_self_loop_rejected(self):
        with self.assertRaises(SpecError):
            Spec.from_dict(spec_dict(
                edges=[{'from': 'customer', 'to': 'customer'}]))

    def test_unknown_element_type_suggests_alternative(self):
        with self.assertRaises(SpecError) as ctx:
            Spec.from_dict(spec_dict(nodes=[{'id': 'a', 'type': 'Klass'}], edges=[]))
        self.assertIn('did you mean', str(ctx.exception))

    def test_unknown_type_allowed_when_not_strict(self):
        spec = Spec.from_dict(spec_dict(nodes=[{'id': 'a', 'type': 'Whatever'}],
                                        edges=[], strict=False))
        self.assertEqual(spec.nodes[0].type, 'Whatever')

    def test_catalog_is_populated(self):
        self.assertGreater(len(type_catalog()), 1000)


class LayoutTest(unittest.TestCase):
    def test_layered_separates_connected_nodes(self):
        spec = layout.layout(Spec.from_dict(spec_dict()))
        left, right = spec.node('customer'), spec.node('order')
        self.assertLess(left.x, right.x)

    def test_grid_wraps_columns(self):
        spec = layout.layout(Spec.from_dict(spec_dict(layout={'mode': 'grid',
                                                             'columns': 2})))
        self.assertEqual(spec.nodes[0].y, spec.nodes[1].y)

    def test_usecase_puts_actors_left(self):
        spec = Spec.from_dict({
            'diagram': 'UseCaseDiagram', 'name': 'U',
            'nodes': [
                {'id': 'actor', 'type': 'Actor', 'name': 'Customer'},
                {'id': 'uc', 'type': 'UseCase', 'name': 'Checkout'},
            ],
            'edges': [{'from': 'actor', 'to': 'uc', 'type': 'Association'}],
        })
        layout.layout(spec)
        self.assertLess(spec.node('actor').x, spec.node('uc').x)

    def test_explicit_keeps_given_coordinates(self):
        spec = Spec.from_dict(spec_dict(nodes=[
            {'id': 'a', 'x': 500, 'y': 400},
            {'id': 'b'},
        ], edges=[], layout={'mode': 'explicit'}))
        layout.layout(spec)
        self.assertEqual((spec.node('a').x, spec.node('a').y), (500, 400))

    def test_every_node_gets_geometry(self):
        spec = layout.layout(Spec.from_dict(spec_dict()))
        for node in spec.nodes:
            for value in (node.x, node.y, node.width, node.height):
                self.assertIsInstance(value, int)


class ProgramTest(unittest.TestCase):
    def setUp(self):
        self.spec = layout.layout(Spec.from_dict(spec_dict()))
        self.lines, self.shapes = to_statements(self.spec)

    def test_header_creates_diagram(self):
        text = '\n'.join(self.lines)
        self.assertIn('createDiagram("ClassDiagram")', text)
        self.assertIn('setName("Order System")', text)

    def test_members_become_create_child(self):
        text = '\n'.join(self.lines)
        self.assertIn('createChild("Attribute")', text)
        self.assertIn('createChild("Operation")', text)
        self.assertIn('setType("long")', text)

    def test_shapes_get_bounds_and_caption(self):
        text = '\n'.join(self.lines)
        self.assertEqual(text.count('setBounds('), 2)
        self.assertEqual(text.count('setRequestResetCaption(true)'), 2)

    def test_edge_links_both_shapes(self):
        text = '\n'.join(self.lines)
        self.assertIn('setFrom($n0)', text)
        self.assertIn('setTo($n1)', text)
        self.assertIn('createConnector(', text)

    def test_saves_and_returns_diagram_id(self):
        self.assertIn('saveProject()', self.lines[-2])
        self.assertEqual(self.lines[-1], '$d.getId()')

    def test_quotes_in_names_are_escaped(self):
        spec = Spec.from_dict(spec_dict(nodes=[{'id': 'a', 'name': 'He said "hi"'}],
                                        edges=[]))
        lines, _ = to_statements(layout.layout(spec))
        self.assertIn('\\"hi\\"', '\n'.join(lines))


class ModelTest(unittest.TestCase):
    def setUp(self):
        self.model = ProjectModel(ET.fromstring(SAMPLE_XML), source='memory')

    def test_summary_counts(self):
        summary = self.model.summary()
        self.assertEqual(summary['project'], 'Demo')
        self.assertEqual(summary['types']['Class'], 1)
        self.assertEqual(summary['types']['Attribute'], 1)

    def test_elements_are_not_duplicated(self):
        names = [e.name for e in self.model.elements(type='Class')]
        self.assertEqual(names, ['Order'])

    def test_diagram_shape_counts(self):
        diagram = self.model.diagrams[0]
        self.assertEqual(diagram.name, 'Class Diagram')
        self.assertEqual(diagram.to_dict()['shapes'], 1)

    def test_path_is_qualified(self):
        element = self.model.elements(type='Attribute')[0]
        self.assertEqual(element.path, 'Domain/Order/total')


class BuilderTest(unittest.TestCase):
    def test_renders_parseable_xml(self):
        builder = ImportBuilder(name='Demo')
        builder.add_class('Order', attributes=[('id', 'long')])
        builder.add_diagram('ClassDiagram', 'Diagram', shapes=[{
            'model_id': 'x', 'type': 'Class', 'name': 'Order'}])
        root = ET.fromstring(builder.render())
        self.assertEqual(root.get('Name'), 'Demo')
        self.assertIsNotNone(root.find('Diagrams/ClassDiagram/Shapes/Class'))
        self.assertEqual(len(builder.rendered_elements()), 3)

    def test_shape_carries_caption(self):
        builder = ImportBuilder()
        builder.add_diagram('ClassDiagram', 'D', shapes=[{
            'model_id': 'x', 'type': 'Class', 'name': 'Order', 'width': 120}])
        shape = ET.fromstring(builder.render()).find('Diagrams/ClassDiagram/Shapes/Class')
        caption = shape.find('Caption')
        self.assertIsNotNone(caption)
        self.assertEqual(caption.get('Visible'), 'true')


class ProfileTest(unittest.TestCase):
    def test_known_diagram_has_native_type(self):
        self.assertEqual(profiles.for_diagram('ActivityDiagram')['node_type'],
                         'ActivityAction')

    def test_unknown_diagram_falls_back(self):
        profile = profiles.for_diagram('NotARealDiagram')
        self.assertEqual(profile['node_type'], 'Class')
        self.assertEqual(profile['layout'], 'grid')


if __name__ == '__main__':
    unittest.main()
