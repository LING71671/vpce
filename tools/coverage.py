"""Measure what actually works, then render the ledger.

    python tools/coverage.py <any-project.vpp> [--render]

Four probes, each a real run inside Visual Paradigm on a temp copy (the source
project is never written):

  1. diagram types   DiagramManager.createDiagram(type) for every constant
  2. element types   IModelElementFactory.create(type), with createChild as the
                     fallback for types the generic factory refuses
  3. commands        com.vp.cmd.* availability under the installed edition
  4. end-to-end      diagram + element + shape + save + render a non-empty PNG,
                     first with the diagram's native element, then with Class

COVERAGE.md is generated from coverage.json, so the document can never claim
more than the last run measured.
"""

import argparse
import json
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpce.app import App  # noqa: E402
from vpce.core import profiles  # noqa: E402
from vpce.core.errors import EditionGate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'coverage.json')
DOC = os.path.join(ROOT, 'COVERAGE.md')

#: keep each bridge call well under the Windows command line limit
ELEMENT_BATCH = 180
#: diagrams per bridge call when building the render matrix
RENDER_BATCH = 12

#: element that renders everywhere, used only to prove the pipeline when the
#: diagram's native element does not draw (see tools/find_shapes.py)
FALLBACK_ELEMENT = 'Class'


def png_size(path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(24)
    except OSError:
        return (0, 0)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return (0, 0)
    return struct.unpack('>II', head[16:24])


def load_json(name):
    with open(os.path.join(ROOT, 'vpce', 'core', name), encoding='utf-8') as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------

def probe_diagram_types(app, types):
    names = sorted(types)
    lines = ['$am = ApplicationManager.instance()', '$dm = $am.getDiagramManager()']
    for name in names:
        lines.append('$dm.createDiagram("%s")' % name)
    raw = app.apis().run('\n'.join(lines) + '\n')
    failed = {}
    for line in raw.splitlines():
        if line.startswith('error#'):
            number = int(line.split('#')[1].split(' ')[0])
            index = number - 3
            if 0 <= index < len(names):
                failed[names[index]] = line.split(' ', 1)[1][:140]
    return {name: {'status': 'failed' if name in failed else 'ok',
                   'message': failed.get(name, '')} for name in names}


def probe_element_types(app, types):
    names = sorted(types)
    detail = {}
    failed = []
    for start in range(0, len(names), ELEMENT_BATCH):
        chunk = names[start:start + ELEMENT_BATCH]
        lines = ['$f = IModelElementFactory.instance()']
        for name in chunk:
            lines.append('$f.create("%s")' % name)
        raw = app.apis().run('\n'.join(lines) + '\n')
        bad = {}
        for line in raw.splitlines():
            if line.startswith('error#'):
                number = int(line.split('#')[1].split(' ')[0])
                offset = number - 2
                if 0 <= offset < len(chunk):
                    bad[chunk[offset]] = line.split(' ', 1)[1][:140]
        for name in chunk:
            if name in bad:
                failed.append((name, bad[name]))
            else:
                detail[name] = {'status': 'ok', 'path': 'create', 'message': ''}
        print('  elements %d/%d' % (min(start + ELEMENT_BATCH, len(names)), len(names)))

    # second chance: a parent can construct what the flat factory refuses
    if failed:
        print('  retrying %d refused types through createChild ...' % len(failed))
        for start in range(0, len(failed), ELEMENT_BATCH):
            chunk = failed[start:start + ELEMENT_BATCH]
            lines = ['$f = IModelElementFactory.instance()',
                     '$p = $f.create("Package")',
                     '$p.setName("coverage-scaffold")']
            for name, _ in chunk:
                lines.append('$p.createChild("%s")' % name)
            raw = app.apis().run('\n'.join(lines) + '\n')
            bad = set()
            for line in raw.splitlines():
                if line.startswith('error#'):
                    number = int(line.split('#')[1].split(' ')[0])
                    offset = number - 4
                    if 0 <= offset < len(chunk):
                        bad.add(chunk[offset][0])
            for name, message in chunk:
                if name in bad:
                    detail[name] = {'status': 'failed', 'path': '', 'message': message}
                else:
                    detail[name] = {'status': 'ok', 'path': 'createChild', 'message': ''}
    return detail


def probe_commands(app):
    out = {}
    for name in app.runtime.available_commands():
        try:
            app.runtime.run(name, [], check=False)
            out[name] = 'ran'
        except EditionGate:
            out[name] = 'edition-gated'
        except Exception:
            out[name] = 'ran'
    return out


def _render_batch(app, project, pairs, work, tag):
    """pairs: [(diagram_type, element_type)] -> {diagram_type: (ntype, px)}"""
    lines = ['$am = ApplicationManager.instance()',
             '$dm = $am.getDiagramManager()',
             '$f = IModelElementFactory.instance()']
    names = []
    for index, (dtype, ntype) in enumerate(pairs):
        name = '%s%d' % (tag, index)
        names.append(name)
        lines.append('$d%d = $dm.createDiagram("%s")' % (index, dtype))
        lines.append('$d%d.setName("%s")' % (index, name))
        lines.append('$e%d = $f.create("%s")' % (index, ntype))
        lines.append('$e%d.setName("%s")' % (index, ntype))
        lines.append('$s%d = $dm.createDiagramElement($d%d, $e%d)' % (index, index, index))
        lines.append('$s%d.setBounds(60, 60, 160, 90)' % index)
        lines.append('$s%d.setRequestResetCaption(true)' % index)
    lines.append('$am.getProjectManager().saveProject()')
    app.apis().run('\n'.join(lines) + '\n')

    files = app.projects().render(diagrams=names, out=work, fmt='png')['files']
    by_name = {os.path.splitext(f['name'])[0]: f['file'] for f in files}
    return {dtype: (ntype, png_size(by_name.get('%s%d' % (tag, index), '')))
            for index, (dtype, ntype) in enumerate(pairs)}


def probe_render(app, project, support, work):
    usable = [name for name, value in sorted(support.items()) if value['status'] == 'ok']
    result = {}

    # pass 1: the diagram's own native element
    for start in range(0, len(usable), RENDER_BATCH):
        pairs = [(dtype, profiles.for_diagram(dtype)['node_type'])
                 for dtype in usable[start:start + RENDER_BATCH]]
        for dtype, (ntype, size) in _render_batch(app, project, pairs, work, 'n').items():
            result[dtype] = {'node_type': ntype, 'px': list(size),
                             'rendered': size[0] > 20, 'role': 'native'}

    # pass 2: fallback element for whatever did not draw
    retry = [dtype for dtype, info in result.items() if not info['rendered']]
    if retry:
        for start in range(0, len(retry), RENDER_BATCH):
            pairs = [(dtype, FALLBACK_ELEMENT) for dtype in retry[start:start + RENDER_BATCH]]
            for dtype, (ntype, size) in _render_batch(app, project, pairs, work, 'f').items():
                if size[0] > 20:
                    result[dtype] = {'node_type': ntype, 'px': list(size),
                                     'rendered': True, 'role': 'fallback'}
    return result


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--only', choices=['diagrams', 'elements', 'commands', 'render'],
                        help='run a single probe and merge into the existing ledger')
    args = parser.parse_args()

    diagram_types = load_json('diagram_types.json')
    model_types = load_json('model_types.json')

    previous = {}
    if args.only and os.path.isfile(DATA):
        with open(DATA, encoding='utf-8') as fh:
            previous = json.load(fh)

    work = os.path.join(os.environ.get('TEMP', '/tmp'), 'vpce-coverage')
    if os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    project = os.path.join(work, 'coverage.vpp')
    shutil.copy2(args.project, project)
    app = App(project=project)

    def wanted(phase):
        return args.only in (None, phase)

    diagrams = (probe_diagram_types(app, diagram_types) if wanted('diagrams')
                else previous.get('diagram_types', {}).get('detail', {}))
    elements = (probe_element_types(app, model_types) if wanted('elements')
                else previous.get('element_types', {}).get('detail', {}))
    commands = (probe_commands(app) if wanted('commands')
                else previous.get('commands', {}).get('detail', {}))

    render = previous.get('render', {}).get('detail', {})
    if args.render and wanted('render'):
        print('render matrix ...')
        render = probe_render(app, project, diagrams, os.path.join(work, 'png'))

    ok_diagrams = sum(1 for v in diagrams.values() if v['status'] == 'ok')
    ok_elements = sum(1 for v in elements.values() if v['status'] == 'ok')
    via_child = sum(1 for v in elements.values() if v.get('path') == 'createChild')
    rendered = sum(1 for v in render.values() if v.get('rendered'))
    native = sum(1 for v in render.values()
                 if v.get('role') == 'native' and v.get('rendered'))
    gated = [k for k, v in commands.items() if v == 'edition-gated']

    data = {
        'vp_home': app.runtime.home,
        'diagram_types': {'total': len(diagrams), 'ok': ok_diagrams, 'detail': diagrams},
        'element_types': {'total': len(elements), 'ok': ok_elements,
                          'via_create_child': via_child, 'detail': elements},
        'commands': {'total': len(commands), 'gated': gated, 'detail': commands},
        'render': {'total': len(render), 'ok': rendered, 'native': native, 'detail': render},
    }
    with open(DATA, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    with open(DOC, 'w', encoding='utf-8') as fh:
        fh.write(render_doc(data))

    print()
    print('diagram types : %d/%d create, %d/%d render'
          % (ok_diagrams, len(diagrams), rendered, ok_diagrams))
    print('element types : %d/%d (createChild fallback: %d)'
          % (ok_elements, len(elements), via_child))
    print('commands      : %d total, %d edition-gated' % (len(commands), len(gated)))
    print('native shapes : %d/%d' % (native, ok_diagrams))
    print('ledger        :', DOC)
    return 0


def render_doc(data):
    diagrams = data['diagram_types']
    elements = data['element_types']
    commands = data['commands']
    render = data.get('render') or {'total': 0, 'ok': 0, 'native': 0, 'detail': {}}

    total_d = diagrams['total'] or 1
    total_e = elements['total'] or 1
    supported = diagrams['ok'] or 1
    runnable = commands['total'] - len(commands['gated'])
    # derive from the per-diagram detail so a stale summary cannot inflate it
    detail = render.get('detail') or {}
    render_ok = sum(1 for v in detail.values() if v.get('rendered'))
    render_native = sum(1 for v in detail.values()
                        if v.get('rendered') and v.get('role') == 'native')

    lines = ['# 覆盖率台账', '',
             '> 由 `python tools/coverage.py <project> --render` 实测生成，只反映**上一次运行**。',
             '> 不要手改本文件。', '',
             '环境：`%s`' % data.get('vp_home', ''), '',
             '## 汇总', '',
             '| 维度 | 通过 | 分母 | 比例 | 说明 |', '|---|---|---|---|---|',
             '| 图类型可创建 | %d | %d | %.1f%% | 其余 %d 个是产品侧 `is not supported` |'
             % (supported, total_d, 100.0 * supported / total_d, total_d - supported),
             '| 图类型可出图 | %d | %d | %.1f%% | 分母为受支持类型；能放入元素并渲染出非空 PNG |'
             % (render_ok, supported, 100.0 * render_ok / supported),
             '| 其中用原生元素 | %d | %d | %.1f%% | 其余靠 `Class` 兜底，配图语义未必正确 |'
             % (render_native, supported, 100.0 * render_native / supported),
             '| 元素类型可创建 | %d | %d | %.1f%% | 含 %d 个只能经 `createChild` 构造 |'
             % (elements['ok'], total_e, 100.0 * elements['ok'] / total_e,
                elements.get('via_create_child', 0)),
             '| 命令行可执行 | %d | %d | %.1f%% | 其余被版本门禁挡住 |'
             % (runnable, commands['total'], 100.0 * runnable / max(1, commands['total'])),
             '']

    if render.get('detail'):
        lines += ['## 端到端出图', '',
                  '| 图类型 | 元素类型 | 方式 | 尺寸 |', '|---|---|---|---|']
        for dtype, info in sorted(render['detail'].items()):
            px = info.get('px') or [0, 0]
            role = '原生' if info.get('role') == 'native' else '兜底'
            lines.append('| %s | %s | %s | %dx%d |'
                         % (dtype, info.get('node_type', ''), role, px[0], px[1]))
        lines.append('')

    lines += ['## 图类型（%d）' % diagrams['total'], '']
    unsupported = [k for k, v in sorted(diagrams['detail'].items())
                   if 'is not supported' in v.get('message', '')]
    other = [(k, v['message']) for k, v in sorted(diagrams['detail'].items())
             if v['status'] != 'ok' and k not in unsupported]
    lines.append('- 可创建：**%d**' % diagrams['ok'])
    lines.append('- 产品侧不支持：**%d**（`UnsupportedOperationException: <类型> is not supported`）'
                 % len(unsupported))
    if other:
        lines.append('- 其它失败：**%d**' % len(other))
    lines.append('')
    if unsupported:
        lines.append('、'.join('`%s`' % n for n in unsupported))
        lines.append('')

    no_shape = [k for k, v in sorted(render.get('detail', {}).items())
                if not v.get('rendered')]
    if no_shape:
        lines += ['## 能建图但放不进元素（编辑器型）', '']
        lines += ['、'.join('`%s`' % n for n in no_shape), '']

    lines += ['## 元素类型（%d）' % elements['total'], '']
    bad = [(k, v['message']) for k, v in sorted(elements['detail'].items())
           if v['status'] != 'ok']
    via_child = [k for k, v in elements['detail'].items() if v.get('path') == 'createChild']
    lines.append('- 可直接 `create()`：**%d**' % (elements['ok'] - len(via_child)))
    lines.append('- 需经 `createChild()`：**%d**%s'
                 % (len(via_child), ('（' + '、'.join('`%s`' % n for n in sorted(via_child)) + '）')
                    if via_child else ''))
    lines.append('- 仍然失败：**%d**' % len(bad))
    if bad:
        lines.append('')
        lines.append('| 类型 | 报错 |')
        lines.append('|---|---|')
        for name, message in bad[:60]:
            lines.append('| %s | %s |' % (name, message.replace('|', '\\|')[:90]))
    lines.append('')

    lines += ['## 命令行门禁', '', '| 命令 | 状态 |', '|---|---|']
    for name, status in sorted(commands['detail'].items()):
        lines.append('| %s | %s |'
                     % (name, '被版本门禁挡住' if status == 'edition-gated' else '可执行'))
    lines.append('')
    lines += ['## 复现', '', '```bash',
              'python java/bridge/build.py',
              'python -m vpce bridge --install',
              'python tools/dump_diagram_types.py <any.vpp>',
              'python tools/coverage.py <any.vpp> --render',
              'python tools/find_shapes.py <any.vpp>      # 找每个图类型的可用元素',
              '```', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    sys.exit(main())
