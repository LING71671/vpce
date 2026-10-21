"""MCP transport (stdio, newline-delimited JSON-RPC 2.0).

Thin: every tool maps onto an App/service call. No Visual Paradigm knowledge
lives here.
"""

import json
import sys
import traceback

from . import __version__
from .app import App
from .core.errors import (CommandFailure, ConfigurationError, EditionGate,
                          ProjectLocked, SpecError, UpgradeRequired, VpceError)
from .core.spec import Spec

PROTOCOL_VERSION = '2024-11-05'
SERVER_INFO = {'name': 'vpce', 'version': __version__}


# --------------------------------------------------------------------------
# handlers
# --------------------------------------------------------------------------

def _app(args):
    return App(vp_home=args.get('vp_home'), project=args.get('project'))


def h_status(args):
    app = _app(args)
    info = app.runtime.describe()
    info['bridge'] = app.bridge_status()['installed']
    if args.get('probe'):
        probe = {}
        for name in ('ExportXML', 'ImportXML', 'ExportDiagramImage', 'Plugin',
                     'ExportXMI', 'InstantReverse'):
            try:
                app.runtime.run(name, [], check=False)
                probe[name] = 'available'
            except EditionGate:
                probe[name] = 'edition-gated'
            except Exception:
                probe[name] = 'available'
        info['probe'] = probe
    return info


def h_summary(args):
    return _app(args).projects().summary(refresh=bool(args.get('refresh')))


def h_model(args):
    rows = _app(args).projects().elements(
        type=args.get('type'), name=args.get('name'), refresh=bool(args.get('refresh')))
    limit = int(args.get('limit') or 200)
    return {'count': len(rows), 'items': rows[:limit], 'truncated': len(rows) > limit}


def h_diagrams(args):
    rows = _app(args).projects().diagrams(refresh=bool(args.get('refresh')))
    return {'count': len(rows), 'items': rows}


def h_export_xml(args):
    return _app(args).projects().export_xml(out_dir=args.get('out'))


def h_images(args):
    return _app(args).projects().render(
        diagrams=args.get('diagram') or '*', out=args['out'], fmt=args.get('format') or 'png')


def h_create_class(args):
    attrs = []
    for item in args.get('attributes') or []:
        name, _, typ = str(item).partition(':')
        attrs.append((name.strip(), typ.strip()))
    return _app(args).projects().create_class(
        args['name'], attributes=attrs, diagram=args.get('diagram'))


def h_import(args):
    return _app(args).projects().import_file(
        args['file'], match_by_name=args.get('match_by_name', True))


def h_upgrade(args):
    return _app(args).projects().upgrade()


def h_api(args):
    script = args.get('script') or ''
    if not script.strip():
        raise VpceError('script is empty')
    return {'response': _app(args).apis().run(script)}


def h_introspect(args):
    return {'text': _app(args).apis().introspect(args['class_name'])}


def h_search(args):
    return {'text': _app(args).apis().search(args['pattern'])}


def h_bridge(args):
    app = _app(args)
    action = args.get('action', 'status')
    if action == 'install':
        return app.install_bridge(force=bool(args.get('force')))
    if action == 'uninstall':
        return app.uninstall_bridge()
    return app.bridge_status()


def h_draw(args):
    app = _app(args)
    if args.get('spec'):
        spec = Spec.from_dict(args['spec'])
    elif args.get('spec_path'):
        spec = Spec.load(args['spec_path'])
    else:
        raise SpecError('vp_draw needs either "spec" or "spec_path"')
    result = app.draw(spec, out=args.get('out'), fmt=args.get('format') or 'png',
                      plan_only=bool(args.get('plan')))
    result.pop('script', None)
    return result


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

TOOLS = [
    {
        'name': 'vp_status',
        'description': 'Locate the Visual Paradigm installation, list its headless command '
                       'classes, report whether the Open API bridge is installed, and optionally '
                       'classify which commands the installed edition allows.',
        'write': False, 'handler': h_status,
        'schema': {
            'type': 'object',
            'properties': {
                'probe': {'type': 'boolean'},
                'vp_home': {'type': 'string'},
            },
        },
    },
    {
        'name': 'vp_project_summary',
        'description': 'Summarise a .vpp project: model element counts by UML type and the diagram list.',
        'write': False, 'handler': h_summary,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'refresh': {'type': 'boolean'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_model_list',
        'description': 'List model elements, optionally filtered by UML type and exact name.',
        'write': False, 'handler': h_model,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'type': {'type': 'string'},
                'name': {'type': 'string'},
                'limit': {'type': 'integer'},
                'refresh': {'type': 'boolean'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_diagram_list',
        'description': 'List diagrams with shape and connector counts.',
        'write': False, 'handler': h_diagrams,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'refresh': {'type': 'boolean'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_export_xml',
        'description': 'Export the whole project model to project.xml.',
        'write': False, 'handler': h_export_xml,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'out': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_export_images',
        'description': 'Render one, several or all diagrams to png/jpg/svg/pdf.',
        'write': False, 'handler': h_images,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'out': {'type': 'string'},
                'diagram': {'type': 'string'},
                'format': {'type': 'string',
                           'enum': ['png', 'png_with_background', 'jpg', 'svg', 'pdf']},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'out'],
        },
    },
    {
        'name': 'vp_draw',
        'description': 'Draw a diagram from a spec: nodes (any UML element type, with attributes '
                       'and operations) plus edges (any relationship type). Handles layout, creates '
                       'real model elements in Visual Paradigm, saves the project, verifies by '
                       're-exporting, and renders an image. One spec covers every diagram type '
                       '(ClassDiagram, UseCaseDiagram, ActivityDiagram, StateDiagram, ERDiagram, '
                       'ComponentDiagram, DeploymentDiagram, MindMapDiagram, ...).',
        'write': True, 'handler': h_draw,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'spec': {
                    'type': 'object',
                    'description': 'inline spec',
                    'properties': {
                        'diagram': {'type': 'string', 'description': 'diagram type, e.g. ClassDiagram'},
                        'name': {'type': 'string', 'description': 'diagram name'},
                        'nodes': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'string'},
                                    'type': {'type': 'string', 'description': 'UML type, e.g. Class / Actor / UseCase'},
                                    'name': {'type': 'string'},
                                    'attributes': {'type': 'array', 'items': {'type': 'string'}},
                                    'operations': {'type': 'array', 'items': {'type': 'string'}},
                                    'x': {'type': 'integer'}, 'y': {'type': 'integer'},
                                    'width': {'type': 'integer'}, 'height': {'type': 'integer'},
                                },
                                'required': ['id'],
                            },
                        },
                        'edges': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'from': {'type': 'string'},
                                    'to': {'type': 'string'},
                                    'type': {'type': 'string', 'description': 'Association / Generalization / Dependency / ...'},
                                    'name': {'type': 'string'},
                                },
                                'required': ['from', 'to'],
                            },
                        },
                        'layout': {'type': 'object'},
                    },
                },
                'spec_path': {'type': 'string', 'description': 'path to a spec JSON instead of inline'},
                'out': {'type': 'string', 'description': 'render output directory'},
                'format': {'type': 'string', 'enum': ['png', 'png_with_background', 'jpg', 'svg', 'pdf']},
                'plan': {'type': 'boolean', 'description': 'layout + script only, no writes'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_create_class',
        'description': 'Create a class through the XML channel (no plugin needed), optionally with a diagram.',
        'write': True, 'handler': h_create_class,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'name': {'type': 'string'},
                'attributes': {'type': 'array', 'items': {'type': 'string'}},
                'diagram': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'name'],
        },
    },
    {
        'name': 'vp_import_xml',
        'description': 'Merge a project XML document into the project file.',
        'write': True, 'handler': h_import,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'file': {'type': 'string'},
                'match_by_name': {'type': 'boolean'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'file'],
        },
    },
    {
        'name': 'vp_upgrade',
        'description': 'Convert an older project to the installed build format.',
        'write': True, 'handler': h_upgrade,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project'],
        },
    },
    {
        'name': 'vp_api',
        'description': 'Run raw Open API statements in a headless Visual Paradigm process. '
                       'The escape hatch: anything under com.vp.plugin.* is callable. '
                       'One statement per line; "$x = expr" stores a variable.',
        'write': True, 'handler': h_api,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'script': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'script'],
        },
    },
    {
        'name': 'vp_api_introspect',
        'description': 'Dump methods and static constants of an Open API class.',
        'write': False, 'handler': h_introspect,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'class_name': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'class_name'],
        },
    },
    {
        'name': 'vp_api_search',
        'description': 'Search the Open API class surface by name fragment.',
        'write': False, 'handler': h_search,
        'schema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'pattern': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
            'required': ['project', 'pattern'],
        },
    },
    {
        'name': 'vp_bridge_status',
        'description': 'Report or change the Open API bridge plugin (status | install | uninstall).',
        'write': True, 'handler': h_bridge,
        'schema': {
            'type': 'object',
            'properties': {
                'action': {'type': 'string', 'enum': ['status', 'install', 'uninstall']},
                'force': {'type': 'boolean'},
                'project': {'type': 'string'},
                'vp_home': {'type': 'string'},
            },
        },
    },
]


def tool_table(allow_write=True):
    return [t for t in TOOLS if allow_write or not t['write']]


def list_tools(allow_write):
    return [{'name': t['name'], 'description': t['description'], 'inputSchema': t['schema']}
            for t in tool_table(allow_write)]


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

class Server(object):
    def __init__(self, allow_write=True, out=None):
        self.allow_write = allow_write
        self.out = out or sys.stdout
        self.handlers = {t['name']: t for t in tool_table(allow_write)}

    def send(self, payload):
        self.out.write(json.dumps(payload, ensure_ascii=False) + '\n')
        self.out.flush()

    def reply(self, msg_id, result=None, error=None):
        payload = {'jsonrpc': '2.0', 'id': msg_id}
        if error is not None:
            payload['error'] = error
        else:
            payload['result'] = result
        self.send(payload)

    def handle(self, msg):
        method = msg.get('method')
        msg_id = msg.get('id')
        params = msg.get('params') or {}
        if method == 'initialize':
            return self.reply(msg_id, {
                'protocolVersion': PROTOCOL_VERSION,
                'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': SERVER_INFO})
        if method in ('notifications/initialized', 'initialized'):
            return None
        if method == 'ping':
            return self.reply(msg_id, {})
        if method == 'tools/list':
            return self.reply(msg_id, {'tools': list_tools(self.allow_write)})
        if method == 'tools/call':
            return self.call_tool(msg_id, params)
        if msg_id is not None:
            return self.reply(msg_id, error={'code': -32601,
                                             'message': 'method not found: %s' % method})
        return None

    def call_tool(self, msg_id, params):
        name = params.get('name')
        args = params.get('arguments') or {}
        spec = self.handlers.get(name)
        if spec is None:
            return self.reply(msg_id, error={'code': -32602, 'message': 'unknown tool: %s' % name})
        try:
            result = spec['handler'](args)
        except EditionGate as exc:
            return self.tool_error(msg_id, 'edition-gated: %s' % exc)
        except UpgradeRequired as exc:
            return self.tool_error(msg_id, '%s (use vp_upgrade first)' % exc)
        except ProjectLocked as exc:
            return self.tool_error(msg_id, '%s (close the project in the GUI)' % exc)
        except (SpecError, ConfigurationError) as exc:
            return self.tool_error(msg_id, str(exc))
        except CommandFailure as exc:
            return self.tool_error(msg_id, str(exc), detail=exc.output[-800:])
        except VpceError as exc:
            return self.tool_error(msg_id, str(exc))
        except Exception as exc:
            return self.tool_error(msg_id, '%s: %s' % (type(exc).__name__, exc),
                                   detail=traceback.format_exc(limit=4))
        return self.reply(msg_id, {'content': [{'type': 'text',
                                                'text': json.dumps(result, indent=2,
                                                                   ensure_ascii=False)}],
                                   'isError': False})

    def tool_error(self, msg_id, message, detail=None):
        body = message if not detail else '%s\n%s' % (message, detail)
        return self.reply(msg_id, {'content': [{'type': 'text', 'text': body}], 'isError': True})


def serve(vp_home=None, allow_write=True, stdin=None, stdout=None):
    import os
    if vp_home:
        os.environ['VPCE_HOME'] = vp_home
    stdin = stdin or sys.stdin
    server = Server(allow_write=allow_write, out=stdout or sys.stdout)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if isinstance(msg, list):
            for item in msg:
                server.handle(item)
        else:
            server.handle(msg)
