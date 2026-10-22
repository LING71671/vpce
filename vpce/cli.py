"""CLI transport. Parses arguments, calls a service, prints a result."""

import argparse
import json
import sys

from . import __version__
from .app import App
from .core.errors import (CommandFailure, ConfigurationError, EditionGate,
                          ProjectLocked, SpecError, UpgradeRequired, VpceError)


def _out(data):
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def _table(rows, columns):
    if not rows:
        sys.stdout.write('(empty)\n')
        return
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ''))) for r in rows)) for c in columns}
    header = '  '.join(str(c).ljust(widths[c]) for c in columns)
    sys.stdout.write(header + '\n' + '-' * len(header) + '\n')
    for row in rows:
        sys.stdout.write('  '.join(str(row.get(c, '')).ljust(widths[c]) for c in columns) + '\n')


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_status(args, app):
    info = app.runtime.describe()
    info['version'] = __version__
    info['bridge'] = app.bridge_status()['installed']
    if args.probe:
        probe = {}
        for name in ('ExportXML', 'ImportXML', 'ExportDiagramImage', 'Plugin',
                     'ExportXMI', 'ImportXMI', 'InstantReverse', 'InstantGenerator'):
            try:
                app.runtime.run(name, [], check=False)
                probe[name] = 'available'
            except EditionGate:
                probe[name] = 'edition-gated'
            except Exception:
                probe[name] = 'available'
        info['probe'] = probe
    _out(info)


def cmd_summary(args, app):
    _out(app.bind(args.project).projects().summary(refresh=args.refresh))


def cmd_export_xml(args, app):
    _out(app.bind(args.project).projects().export_xml(out_dir=args.out))


def cmd_elements(args, app):
    rows = app.bind(args.project).projects().elements(
        type=args.type, name=args.name, refresh=args.refresh)
    if args.text:
        _table(rows, ('type', 'name', 'id'))
    else:
        _out(rows)


def cmd_diagrams(args, app):
    rows = app.bind(args.project).projects().diagrams(refresh=args.refresh)
    if args.text:
        _table(rows, ('type', 'name', 'shapes', 'connectors'))
    else:
        _out(rows)


def cmd_images(args, app):
    _out(app.bind(args.project).projects().render(
        diagrams=args.diagram or '*', out=args.out, fmt=args.format))


def cmd_import(args, app):
    _out(app.bind(args.project).projects().import_file(
        args.file, match_by_name=not args.no_match))


def cmd_create_class(args, app):
    attrs = []
    for item in args.attribute or []:
        name, _, typ = item.partition(':')
        attrs.append((name.strip(), typ.strip()))
    report = app.bind(args.project).projects().create_class(
        args.name, attributes=attrs, diagram=args.diagram)
    _out(report)
    return 0 if not report['missing'] else 2


def cmd_upgrade(args, app):
    _out(app.bind(args.project).projects().upgrade())


def cmd_draw(args, app):
    app.bind(args.project)
    result = app.draw(args.spec, out=args.out, fmt=args.format, plan_only=args.plan)
    if args.script:
        sys.stdout.write(result.pop('script') + '\n')
        _out({k: v for k, v in result.items() if k != 'script'})
    else:
        result.pop('script', None)
        _out(result)
    return 0


def cmd_api(args, app):
    app.bind(args.project)
    if args.file:
        with open(args.file, encoding='utf-8') as fh:
            script = fh.read()
    elif args.expr:
        script = '\n'.join(args.expr) + '\n'
    else:
        raise VpceError('needs an expression or --file')
    sys.stdout.write(app.apis().run(script))
    return 0


def cmd_introspect(args, app):
    sys.stdout.write(app.bind(args.project).apis().introspect(args.cls, refresh=args.refresh) + '\n')
    return 0


def cmd_search(args, app):
    sys.stdout.write(app.bind(args.project).apis().search(args.pattern, refresh=args.refresh) + '\n')
    return 0

def cmd_bridge(args, app):
    if args.install:
        _out(app.install_bridge(force=args.force))
    elif args.uninstall:
        _out(app.uninstall_bridge())
    else:
        if args.project:
            app.bind(args.project)
        _out(app.bridge_status())
    return 0


def cmd_mcp(args, app):
    from .mcp_server import serve
    serve(vp_home=args.vp_home, allow_write=not args.read_only)
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog='vpce',
        description='Headless control for Visual Paradigm: read projects, write models, '
                    'draw any diagram from a JSON spec.')
    parser.add_argument('--vp-home', help='Visual Paradigm installation directory')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command')

    def add(name, func, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(func=func)
        return sp

    sp = add('status', cmd_status, 'installation info and edition-gate probe')
    sp.add_argument('--probe', action='store_true')

    sp = add('summary', cmd_summary, 'project overview')
    sp.add_argument('project')
    sp.add_argument('--refresh', action='store_true')

    sp = add('export-xml', cmd_export_xml, 'write the project model to XML')
    sp.add_argument('project')
    sp.add_argument('--out')

    sp = add('elements', cmd_elements, 'list model elements')
    sp.add_argument('project')
    sp.add_argument('--type')
    sp.add_argument('--name')
    sp.add_argument('--refresh', action='store_true')
    sp.add_argument('--text', action='store_true')

    sp = add('diagrams', cmd_diagrams, 'list diagrams')
    sp.add_argument('project')
    sp.add_argument('--refresh', action='store_true')
    sp.add_argument('--text', action='store_true')

    sp = add('images', cmd_images, 'render diagrams to image files')
    sp.add_argument('project')
    sp.add_argument('--out', required=True)
    sp.add_argument('--diagram')
    sp.add_argument('--format', default='png',
                    choices=['png', 'png_with_background', 'jpg', 'svg', 'pdf'])

    sp = add('import', cmd_import, 'merge an XML document into the project')
    sp.add_argument('project')
    sp.add_argument('--file', required=True)
    sp.add_argument('--no-match', action='store_true')

    sp = add('create-class', cmd_create_class, 'create a class via the XML channel')
    sp.add_argument('project')
    sp.add_argument('name')
    sp.add_argument('--attribute', action='append', metavar='NAME[:TYPE]')
    sp.add_argument('--diagram')

    sp = add('upgrade', cmd_upgrade, 'convert the project to the installed build')
    sp.add_argument('project')

    sp = add('draw', cmd_draw, 'draw a diagram from a JSON spec (AI-authored)')
    sp.add_argument('spec', help='path to the spec JSON')
    sp.add_argument('--project', required=True)
    sp.add_argument('--out', help='render the result to this directory')
    sp.add_argument('--format', default='png',
                    choices=['png', 'png_with_background', 'jpg', 'svg', 'pdf'])
    sp.add_argument('--plan', action='store_true', help='layout + script only, no writes')
    sp.add_argument('--script', action='store_true', help='print the generated statements')

    sp = add('api', cmd_api, 'run Open API statements inside a headless VP')
    sp.add_argument('project')
    sp.add_argument('expr', nargs='*')
    sp.add_argument('--file')

    sp = add('introspect', cmd_introspect,
             'dump methods and constants of one or more Open API classes')
    sp.add_argument('project')
    sp.add_argument('cls', nargs='+', metavar='class')
    sp.add_argument('--refresh', action='store_true', help='ignore the discovery cache')

    sp = add('search', cmd_search, 'find Open API classes by name fragment')
    sp.add_argument('project')
    sp.add_argument('pattern', nargs='+', metavar='pattern')
    sp.add_argument('--refresh', action='store_true', help='ignore the discovery cache')

    sp = add('bridge', cmd_bridge, 'install/inspect the Open API bridge plugin')
    sp.add_argument('project', nargs='?')
    sp.add_argument('--install', action='store_true')
    sp.add_argument('--uninstall', action='store_true')
    sp.add_argument('--force', action='store_true')

    sp = add('mcp', cmd_mcp, 'run the MCP server on stdio')
    sp.add_argument('--read-only', action='store_true')

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, 'func', None):
        parser.print_help()
        return 1
    app = App(vp_home=args.vp_home, project=getattr(args, 'project', None))
    try:
        return args.func(args, app) or 0
    except EditionGate as exc:
        _out({'error': 'edition-gated', 'message': str(exc)})
    except UpgradeRequired as exc:
        _out({'error': 'upgrade-required', 'message': str(exc),
              'hint': 'vpce upgrade <project>'})
    except ProjectLocked as exc:
        _out({'error': 'project-locked', 'message': str(exc),
              'hint': 'close the project in the GUI first'})
    except SpecError as exc:
        _out({'error': 'bad-spec', 'message': str(exc)})
    except ConfigurationError as exc:
        _out({'error': 'config', 'message': str(exc)})
    except CommandFailure as exc:
        _out({'error': 'command-failed', 'message': str(exc), 'output': exc.output})
    except VpceError as exc:
        _out({'error': 'vpce', 'message': str(exc)})
    return 2


if __name__ == '__main__':
    sys.exit(main())
