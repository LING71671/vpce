"""Per-diagram-type defaults.

A class diagram and a use case diagram do not want the same layout: actors
belong outside the ellipse cluster, mind maps want a centre, activity chains
want to fall downward. The profile table is data, not code branching, so
adding a diagram type is one dict entry.

`node_type` values are only listed where the name was verified against
`IModelElementFactory`'s MODEL_TYPE constants (see core/model_types.json).
Diagram types without an entry fall back to DEFAULT_PROFILE and the caller is
expected to name each node's type explicitly.
"""

DEFAULT_PROFILE = {
    'layout': 'grid',
    'node_type': 'Class',
    'direction': 'horizontal',
}

PROFILES = {
    # structural
    'ClassDiagram': {'layout': 'layered', 'node_type': 'Class'},
    'PackageDiagram': {'layout': 'layered', 'node_type': 'Package'},
    'ObjectDiagram': {'layout': 'layered', 'node_type': 'Object'},
    'ComponentDiagram': {'layout': 'layered', 'node_type': 'Component'},
    'DeploymentDiagram': {'layout': 'layered', 'node_type': 'Node'},
    'CompositeStructureDiagram': {'layout': 'layered', 'node_type': 'Class'},
    'ProfileDiagram': {'layout': 'layered', 'node_type': 'Class'},

    # behaviour -- chains read top to bottom.
    # Action renders as an empty shape in ActivityDiagram; ActivityAction is the
    # one that actually draws. Same for Flowchart. Verified by tools/probe_shape_types.py.
    'ActivityDiagram': {'layout': 'layered', 'node_type': 'ActivityAction', 'direction': 'vertical'},
    'StateDiagram': {'layout': 'layered', 'node_type': 'State', 'direction': 'vertical'},
    'Flowchart': {'layout': 'layered', 'node_type': 'ActivityAction', 'direction': 'vertical'},
    'BusinessProcessDiagram': {'layout': 'layered', 'node_type': 'Activity'},

    # data
    'ERDiagram': {'layout': 'layered', 'node_type': 'DBTable'},
    'ChenNotationERD': {'layout': 'layered', 'node_type': 'ChenERDEntity'},
    'ORMDiagram': {'layout': 'layered', 'node_type': 'Class'},

    # actors first
    'UseCaseDiagram': {'layout': 'usecase', 'node_type': 'UseCase'},
    'UseCaseDescriptionDiagram': {'layout': 'usecase', 'node_type': 'UseCase'},

    # radial
    'MindMapDiagram': {'layout': 'radial', 'node_type': 'MindMapNode'},
    'MindMappingDiagram': {'layout': 'radial', 'node_type': 'MindMapNode'},

    # interaction -- lifelines side by side
    'InteractionDiagram': {'layout': 'grid', 'node_type': 'InteractionLifeLine'},
    'CommunicationDiagram': {'layout': 'grid', 'node_type': 'Actor'},
    'TimingDiagram': {'layout': 'grid', 'node_type': 'InteractionLifeLine'},

    # requirements and planning
    'RequirementDiagram': {'layout': 'grid', 'node_type': 'Requirement'},
    'UserStoryMapDiagram': {'layout': 'grid', 'node_type': 'UserStory'},
}


def for_diagram(diagram_type):
    profile = dict(DEFAULT_PROFILE)
    profile.update(PROFILES.get(diagram_type, {}))
    return profile
