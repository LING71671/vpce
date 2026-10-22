# 接口文档

vpce 有三层接口，能力等价：

| 层 | 入口 | 适合 |
|---|---|---|
| CLI | `python -m vpce <命令>` | 脚本、CI、人工调试 |
| MCP | `python -m vpce mcp`（stdio） | AI 客户端直接调用 |
| Python | `vpce.app.App` + service | 嵌进别的程序 |

---

## 1. CLI

### 1.1 全局

```
vpce [-h] [--vp-home VP_HOME] [--version] <command> ...
```

| 参数 | 说明 |
|---|---|
| `--vp-home` | Visual Paradigm 安装目录。不填则依次看 `VPCE_HOME`、`VP_HOME`、常见默认路径 |

退出码：`0` 成功；`1` 未给子命令；`2` 失败（错误以 JSON 打到 stdout）。

所有命令的输出都是 JSON（`api` / `introspect` / `search` 输出纯文本）。

### 1.2 命令

#### `status`
```
vpce status [--probe]
```
返回安装信息。`--probe` 会真的调一遍关键命令，标出哪些被版本门禁挡住（每次探测起一个 JVM，约 40 秒）。

```json
{
  "home": "E:\\Visual Paradigm CE 18.1",
  "java": "E:\\Visual Paradigm CE 18.1\\jre\\bin\\java.exe",
  "jars": 20,
  "commands": ["ExportXML", "ImportXML", "ExportDiagramImage", "Plugin", "..."],
  "bridge": true,
  "probe": {"ExportXML": "available", "ExportXMI": "edition-gated"}
}
```

#### `summary`
```
vpce summary <project> [--refresh]
```
```json
{
  "project": "Order System",
  "uml_version": "2.x",
  "model_elements": 384,
  "types": {"Class": 5, "Attribute": 13, "Association": 4},
  "diagrams": [{"type": "ClassDiagram", "id": "...", "name": "Order System",
                "shapes": 5, "connectors": 4, "shape_types": {"Class": 5}}]
}
```
`--refresh` 忽略 XML 缓存重新导出。

#### `diagrams` / `elements`
```
vpce diagrams <project> [--refresh] [--text]
vpce elements <project> [--type T] [--name N] [--refresh] [--text]
```
`--text` 打表格，否则打 JSON 数组。

#### `draw`
```
vpce draw <spec.json> --project <project> [--out DIR] [--format FMT]
           [--plan] [--script]
```
画一张图。参数见 §3。

| 参数 | 说明 |
|---|---|
| `--out` | 导出目录；给了就渲染 PNG |
| `--format` | `png` / `png_with_background` / `jpg` / `svg` / `pdf`，默认 `png` |
| `--plan` | 只排版 + 生成语句，不写工程 |
| `--script` | 把下发的语句打到 stdout |

```json
{
  "diagram": {"diagram": "ClassDiagram", "name": "Order System", "nodes": 5,
              "edges": 4, "node_types": {"Class": 5}, "edge_types": {"Association": 4}},
  "diagram_id": "lJrXeoWF0PGY_QfG",
  "statements": 97,
  "verify": {"elements_found": ["Customer", "Order"],
             "elements_missing": [],
             "diagrams_found": ["Order System"],
             "diagrams_missing": []},
  "images": [{"file": "E:\\vpce\\demo\\final\\Order_System.png",
              "name": "Order_System.png", "bytes": 22122}]
}
```

#### `images`
```
vpce images <project> --out DIR [--diagram NAME] [--format FMT]
```
不写 `--diagram` 就是全部图。返回 `{"out": "...", "files": [{"file","name","bytes"}]}`。

#### `export-xml`
```
vpce export-xml <project> [--out DIR]
```
返回 `{"xml": "<path>/project.xml", "bytes": 174992}`。

#### `import`
```
vpce import <project> --file <patch.xml> [--no-match]
```
把 XML 合并进工程（默认按名字匹配）。返回 `{"backup": "...", "summary": {...}}`。

#### `create-class`
```
vpce create-class <project> <name> [--attribute NAME[:TYPE]] [--diagram NAME]
```
走 XML 通道，不需要插件。返回 `{elements_found, elements_missing, diagrams_found,
diagrams_missing, backup, missing}`。

#### `upgrade`
```
vpce upgrade <project>
```
老工程转成当前 build 的格式，先备份。返回 `{"backup": "...", "summary": {...}}`。

#### `bridge`
```
vpce bridge [project] [--install] [--uninstall] [--force]
```
`--install` 把编译好的插件复制到 `%APPDATA%\VisualParadigm\plugins\com.vpce.bridge`；
`--uninstall` 删掉；不带参数看状态。

```json
{"installed": true,
 "plugin_root": "C:\\Users\\...\\AppData\\Roaming\\VisualParadigm\\plugins",
 "build": "E:\\vpce\\java\\bridge\\out\\com.vpce.bridge",
 "probe": "r1 = d[class=v.bgg.d] ..."}
```

#### `api`
```
vpce api <project> 'expr1' 'expr2' ...
vpce api <project> --file script.vpce
```
跑 Open API 语句，原样输出插件返回的文本（含 `error#N`）。语法见 §4。

#### `introspect` / `search`
```
vpce introspect <project> <class>     # 列方法 + 静态常量（含实际值）
vpce search <project> <pattern>       # 在 com.vp.plugin.** 里按名字片段找类
```

#### `mcp`
```
vpce mcp [--read-only]
```
stdio 启动 MCP 服务。`--read-only` 隐藏 5 个写工具。

---

## 2. MCP

- 传输：stdio，一行一条 JSON-RPC 2.0
- `protocolVersion`：`2024-11-05`
- `serverInfo`：`{"name": "vpce", "version": "0.3.0"}`

### 2.1 方法

| 方法 | 说明 |
|---|---|
| `initialize` | 握手，返回协议版本与能力 |
| `notifications/initialized` | 忽略 |
| `ping` | 返回 `{}` |
| `tools/list` | 工具清单 |
| `tools/call` | 调工具：`{"name": "...", "arguments": {...}}` |

### 2.2 工具

| 工具 | 写 | 参数 |
|---|---|---|
| `vp_status` | 否 | `probe?`, `vp_home?` |
| `vp_project_summary` | 否 | `project*`, `refresh?`, `vp_home?` |
| `vp_model_list` | 否 | `project*`, `type?`, `name?`, `limit?`, `refresh?` |
| `vp_diagram_list` | 否 | `project*`, `refresh?` |
| `vp_export_xml` | 否 | `project*`, `out?` |
| `vp_export_images` | 否 | `project*`, `out*`, `diagram?`, `format?` |
| `vp_api_introspect` | 否 | `project*`, `class_name*` |
| `vp_api_search` | 否 | `project*`, `pattern*` |
| `vp_draw` | 是 | `project*`, `spec*` 或 `spec_path*`, `out?`, `format?`, `plan?` |
| `vp_create_class` | 是 | `project*`, `name*`, `attributes?`, `diagram?` |
| `vp_import_xml` | 是 | `project*`, `file*`, `match_by_name?` |
| `vp_upgrade` | 是 | `project*` |
| `vp_api` | 是 | `project*`, `script*` |
| `vp_bridge_status` | 是 | `action?`（status/install/uninstall）, `force?`, `project?` |

`*` 必填。

### 2.3 成功与失败

成功：

```json
{"jsonrpc": "2.0", "id": 4, "result": {
  "content": [{"type": "text", "text": "{\"diagram\": {...}}"}],
  "isError": false
}}
```

工具内部失败（工程锁、版本门禁、规格错误）：**仍是 HTTP 层成功**，用 `isError: true`：

```json
{"jsonrpc": "2.0", "id": 5, "result": {
  "content": [{"type": "text", "text": "project is locked by another process (close the project in the GUI)"}],
  "isError": true
}}
```

只有「工具名不存在」才是 JSON-RPC 层错误：`{"code": -32602, "message": "unknown tool: x"}`。

### 2.4 客户端配置

```json
{
  "mcpServers": {
    "vpce": {
      "command": "python",
      "args": ["-m", "vpce", "mcp"],
      "cwd": "E:/vpce",
      "env": {"VPCE_HOME": "E:/Visual Paradigm CE 18.1"}
    }
  }
}
```

---

## 3. 画图规格（`vpce draw` 的输入）

### 3.1 结构

```json
{
  "diagram": "ClassDiagram",
  "name": "Order System",
  "nodes": [
    {"id": "customer", "type": "Class", "name": "Customer",
     "attributes": ["id:long"], "operations": ["placeOrder"]}
  ],
  "edges": [
    {"from": "customer", "to": "order", "type": "Association", "name": "places"}
  ],
  "layout": {"mode": "layered", "x": 40, "y": 40, "columns": 3},
  "strict": true
}
```

### 3.2 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `diagram` | 是 | 图类型，如 `ClassDiagram`。受支持且能出图的 29 个见 `skills/vpce-diagram-authoring/references/diagram-recipes.md` |
| `name` | 否 | 图名，默认 `Diagram` |
| `nodes[].id` | 是 | 唯一，`[A-Za-z_][\w.-]*`，只用于连边 |
| `nodes[].type` | 否 | 元素类型，默认取图类型的原生元素 |
| `nodes[].name` | 否 | 图上显示的名字，默认同 `id` |
| `nodes[].attributes` | 否 | `"名字:类型"` 或 `{"name","type"}` |
| `nodes[].operations` | 否 | 只写名字，VP 自动补括号 |
| `nodes[].stereotype` | 否 | 构造型名字 |
| `nodes[].x/y/width/height` | 否 | 精确几何；不给由布局算 |
| `edges[].from` / `to` | 是 | 必须是已定义的 `nodes[].id` |
| `edges[].type` | 否 | 关系类型，默认 `Association` |
| `edges[].name` | 否 | 关系名 |
| `layout.mode` | 否 | `layered` / `grid` / `usecase` / `radial` / `explicit` |
| `layout.columns` | 否 | `grid` 的列数 |
| `layout.x` / `y` | 否 | 原点，默认 `40, 40` |
| `strict` | 否 | 默认 `true`，校验元素类型是否在 1455 个合法名里 |

### 3.3 校验规则

`Spec.validate()` 在写工程**之前**拦下这些：

- `nodes[].id` 重复
- `edges` 的端点不是已定义的 id
- 自环（`from == to`）
- 元素类型不在 `model_types.json` 里 —— 报 `unknown element type 'X'; did you mean ...`
- 没有节点

### 3.4 布局

| mode | 行为 |
|---|---|
| `layered` | 按边的方向分列（BFS 层级）。`ActivityDiagram`/`StateDiagram`/`Flowchart` 走纵向 |
| `grid` | 列优先网格，`columns` 控制列数 |
| `usecase` | `Actor` 排左列，其余在右侧网格 |
| `radial` | 第一个节点居中，其余绕环 |
| `explicit` | 全用 `x/y`，缺的按顺序排开 |

不给 `mode` 时按图类型取默认（`core/profiles.py`）。

---

## 4. Open API 语句（`vpce api` / `vp_api`）

### 4.1 语法

| 形式 | 含义 |
|---|---|
| `expr` | 一行一句，逐行执行 |
| `$name = expr` | 存变量，后续 `$name` 引用 |
| `@introspect <类>` | 列方法与静态常量（常量打印实际值） |
| `@search <片段>` | 在 classpath 的 `com.vp.plugin.**` 里找类 |
| `//` 或 `#` 开头 | 注释 |

表达式是链式调用：`a.b().c().d()`，无参方法可省括号（`$d.getName`）。

实参支持：`"字符串"`、整数、浮点、`true`/`false`、`null`、`$var`、
`Class.CONSTANT`（自动按静态常量解析）。

### 4.2 返回

每行一句返回一行：

```
$am = d[class=v.bgg.d] v.bgg.d@2c1ea7be
r2 = String 42
r3 = null
error#4 java.lang.UnsupportedOperationException: CRCCardDiagram is not supported.
```

- `rN` 里的 N 是语句序号
- `error#N` 会剥掉反射包装，直接给根因
- `String` / `Integer` / `Boolean` 是原始值；对象给 `类名(id=..., name=..., class=...)`

### 4.3 类名解析顺序

1. 原样
2. `com.vp.plugin.` + 名字
3. `com.vp.plugin.model.` / `.diagram.` / `.diagram.shape.` / `.view.` / `.action.` + 名字
4. 逐级截断最后一段再试（处理 `a.b.C.D` 形式）
5. 按简名在全部 `com.vp.plugin.**` 里查索引

所以 `IDiagram`、`IModelElementFactory`、`ApplicationManager` 都能直接写。

### 4.4 传输上限

整个脚本 base64 后作为**一个** `-pluginargs` 参数传入（参数按空格切分，所以只能单 token）。
Windows 命令行约 32K 字符，脚本原文超过约 20KB 就要分批。

---

## 5. 错误分类

CLI 的错误输出：

```json
{"error": "project-locked", "message": "...", "hint": "close the project in the GUI first"}
```

| `error` | 触发 | 处理 |
|---|---|---|
| `edition-gated` | 该版本不支持此命令 | 换方案，别重试 |
| `upgrade-required` | 工程文件是旧版本 | `vpce upgrade` |
| `project-locked` | 工程被 GUI 占用 | 关 GUI 或换副本 |
| `bad-spec` | 规格不合法 | 按 message 改 JSON |
| `config` | 找不到安装 / 插件布局不对 | 设 `VPCE_HOME` / 重装插件 |
| `command-failed` | VP 命令返回非 0 或含 `failed!` | 看 `output` 字段 |
| `vpce` | 其它（如插件没装） | 按 message |

MCP 侧同一套异常映射成 `isError: true` 的文本，前缀分别是
`edition-gated:`、`upgrade-required`、`project-locked` 等。

---

## 6. 产物文件

### `coverage.json`

`tools/coverage.py` 的原始结果，`COVERAGE.md` 由它渲染：

```json
{
  "vp_home": "...",
  "diagram_types": {"total": 106, "ok": 31,
                    "detail": {"ClassDiagram": {"status": "ok", "message": ""}}},
  "element_types": {"total": 1455, "ok": 1455, "via_create_child": 4,
                    "detail": {"Sprint": {"status": "ok", "path": "createChild", "message": ""}}},
  "commands": {"total": 28, "gated": ["ExportXMI"], "detail": {"ExportXML": "ran"}},
  "render": {"total": 31, "ok": 29, "native": 29,
             "detail": {"ClassDiagram": {"node_type": "Class", "px": [166, 96],
                                          "rendered": true, "role": "native"}}}
}
```

### 缓存

导出的 `project.xml` 存在 `%TEMP%\vpce-cache\<路径哈希>\`，按工程 mtime+size 失效。

### 备份

- `vpce import` / `vpce create-class`：写前生成 `<工程>.bak-<时间戳>`
- `vpce upgrade`：同上
- Visual Paradigm 自己还会生成 `.bak_XXXX`（插件/命令写入时）
