# vpce — 让 AI 直接操控 Visual Paradigm 画图

给出一个 JSON 规格，AI 就能在真实的 Visual Paradigm CE 里建模型、建图、连关系、保存、导出 PNG。
全程无 GUI、无键鼠模拟、无人参与。

```
vpce draw examples/order-system.json --project demo.vpp --out png/
```

产物：5 个类（含属性、操作）、4 条关联、分层的类图，以及一张渲染好的 PNG。

已验证环境：**Visual Paradigm Community Edition 18.1 (build 20261011)，Windows 11，内置 Temurin JRE 11.0.16.1**。

文档索引：

| 文件 | 内容 |
|---|---|
| `docs/API.md` | 接口文档：CLI 每个命令、14 个 MCP 工具、规格 schema、Open API 语句语法、错误分类、产物格式 |
| `ARCHITECTURE.md` | 五层分层与依赖规则、加功能时的落点 |
| `COVERAGE.md` | 覆盖率台账（脚本生成，不许手改） |
| `skills/vpce-diagram-authoring/` | 给 AI 用的技能包：选型表、规格写法、验收清单、报错处置 |
| `tools/README.md` | 十个测量/诊断脚本各自做什么 |
| `README.en.md` · `CHANGELOG.md` · `CONTRIBUTING.md` · `SECURITY.md` | 英文说明、版本记录、贡献指南、安全策略 |

---

## 1. 两条通道

| 通道 | 载体 | 能做什么 | 前置 |
|---|---|---|---|
| **XML** | `ExportXML` / `ImportXML` / `ExportDiagramImage` | 读全量模型、按 XML 写元素、导出图 | 无 |
| **Open API** | 插件 `com.vpce.bridge`，由 `com.vp.cmd.Plugin` 载入 | 建图、建任意元素、连线、定位、保存、反射调用任意 API | `vpce bridge --install` 装一次 |

`draw` 走 Open API；读写模型、出图也能走 XML。两条互为验证：写完用另一条回读。

## 2. 安装

```bash
python java/bridge/build.py        # 用 VP 自带 javac 编译插件
python -m vpce bridge --install    # 装到 %APPDATA%\VisualParadigm\plugins\com.vpce.bridge
python -m vpce status              # 确认能找到安装与命令
```

安装位置解析顺序：`--vp-home` → `VPCE_HOME` / `VP_HOME` → 安装器写的注册表项 →
扫常见安装根目录。不写死盘符。

## 3. 画图：规格即图纸

AI 只需要产出这样一个对象（MCP 的 `vp_draw` 可直接收 JSON，CLI 收文件）：

```json
{
  "diagram": "ClassDiagram",
  "name": "Order System",
  "nodes": [
    {"id": "customer", "type": "Class", "name": "Customer",
     "attributes": ["id:long", "email:string"], "operations": ["placeOrder"]},
    {"id": "order", "type": "Class", "name": "Order",
     "attributes": ["total:double"]}
  ],
  "edges": [
    {"from": "customer", "to": "order", "type": "Association", "name": "places"}
  ],
  "layout": {"mode": "layered"}
}
```

- `diagram`：图类型。常量共 106 个，**这个 CE 版本支持其中 31 个**（详见 §6 覆盖率），
  受支持的有 `ClassDiagram`、`UseCaseDiagram`、`ActivityDiagram`、`StateDiagram`、`ERDiagram`、
  `ComponentDiagram`、`DeploymentDiagram`、`PackageDiagram`、`ObjectDiagram`、`InteractionDiagram` …
- `nodes[].type`：任意模型元素类型。工厂接受 **1455** 个类型名，清单在
  `vpce/core/model_types.json`；写错会直接报错并给出相近建议，不会静默生成一张空图。
- `edges[].type`：`Association` / `Generalization` / `Dependency` / 其它关系类型。
- `layout.mode`：`layered`（默认，按边分层）、`grid`、`usecase`（角色靠左）、`radial`（思维导图）、
  `explicit`（自己给坐标）。不填则按图类型取默认画像（`core/profiles.py`）。

每个图类型自带排版画像，所以同类图不用每次调坐标：

| 图类型 | 默认布局 | 默认元素类型 |
|---|---|---|
| `ClassDiagram` | layered | Class |
| `UseCaseDiagram` | usecase（Actor 左列） | UseCase |
| `ActivityDiagram` / `StateDiagram` / `Flowchart` | layered 纵向 | Action / State |
| `ERDiagram` | layered | DBTable |
| `MindMapDiagram` | radial | MindMapNode |
| `InteractionDiagram` | grid | InteractionLifeLine |

## 4. CLI

```
vpce status [--probe]                 安装信息 + 版本门禁探测
vpce summary <project>                元素计数 + 图清单
vpce diagrams <project> [--text]      图列表
vpce elements <project> --text        元素列表
vpce draw <spec.json> --project P     画图（--plan 只排版不落盘，--script 打印生成的语句）
vpce images <project> --out DIR       导出图
vpce export-xml <project> --out DIR   导出模型 XML
vpce import <project> --file X.xml    合并 XML
vpce create-class <project> NAME      走 XML 通道建类
vpce upgrade <project>                老工程升级
vpce api <project> '$expr'            直接跑 Open API 语句
vpce introspect <project> IDiagram    看某个 API 类的方法与常量
vpce search <project> Diagram         按名字找 API 类
vpce bridge [--install|--uninstall]   插件管理
vpce mcp                              启动 MCP（--read-only 隐藏写工具）
```

`--plan` 是给 AI 自检用的：不写工程，只返回排版后的脚本，可以先看再落盘。

## 5. MCP

```json
{
  "mcpServers": {
    "vpce": {
      "command": "python",
      "args": ["-m", "vpce", "mcp"],
      "cwd": "/path/to/vpce",
      "env": { "VPCE_HOME": "/path/to/Visual Paradigm" }
    }
  }
}
```

`VPCE_HOME` 可以不填——会自动从注册表和常见安装目录找。

14 个工具：

| 类别 | 工具 |
|---|---|
| 画 | `vp_draw`（规格 → 图 + PNG + 回读校验） |
| 读 | `vp_project_summary`、`vp_model_list`、`vp_diagram_list`、`vp_export_xml`、`vp_export_images` |
| 写 | `vp_create_class`、`vp_import_xml`、`vp_upgrade` |
| 发现 | `vp_status`、`vp_api_search`、`vp_api_introspect`、`vp_bridge_status` |
| 逃生口 | `vp_api`（任意 Open API 语句） |

## 6. 覆盖率台账

`COVERAGE.md` 由 `tools/coverage.py` 实测生成，不接受手写。当前环境（CE 18.1）的数字：

| 维度 | 通过 | 分母 | 覆盖率 | 说明 |
|---|---|---|---|---|
| 图类型可创建 | 31 | 106 | 29.2% | 其余 75 个是**产品侧** `is not supported` |
| 图类型可出图 | 29 | 31 | 93.5% | 能放入元素并渲染出非空 PNG |
| 元素类型可创建 | 1455 | 1455 | **100%** | 1451 直接 create，4 个走 createChild |
| 命令行可执行 | 11 | 28 | 39.3% | 17 个被版本门禁挡住 |

两件事必须说清楚：

- **106 是常量个数，不是能画的图数。** 这个 CE 版本只有 31 个图类型真的能建；
  另外 75 个直接抛 `UnsupportedOperationException: <类型> is not supported`。
- **31 个受支持类型里，29 个能真正出图**；剩下 `CRCCardDiagram` 和 `EAProcessStepDiagram`
  是编辑器型图，用原生元素、`Class` 兜底、类型专属元素（`CRCCard`）都试过，一律空图——
  它们不接受模型元素形状。所以「能承载元素的图类型」这一档是 **29/29 = 100%**。

```bash
python tools/coverage.py <any.vpp> --render   # 重新测量并重写台账
python tools/find_shapes.py <any.vpp>         # 逐轮找每个图类型能画出的元素
python tools/regen_doc.py                     # 只按 coverage.json 重写文档
```

## 7. 边界（实测）

| 命令 | CE 18.1 |
|---|---|
| `ExportXML` / `ImportXML` / `ExportDiagramImage` | 可用 |
| `Plugin`（Open API） | 可用 |
| `ExportXMI` / `ImportXMI` | 被挡：`Feature not supported by current edition` |
| `InstantReverse` / `InstantGenerator` | 被挡 |

其它限制：

- 导出图片右下角有 CE 水印。
- 工程不能同时被 GUI 打开，否则 `Project file locked`。
- 每次调用要起一个 JVM（7–10 s）；批量操作应合并成一个规格或一个脚本。
- 连接线走 VP 默认直线路由；要绕行得传 waypoint（`vp_api` 可做，尚未封装）。
- 序列图的 lifeline/message 需要按 `InteractionLifeLine` / `Message` 组合，规格里显式写类型即可，
  但自动排版还不如类图成熟。

## 8. 测试

```bash
python -m unittest discover -s tests -p "test_core.py" -v   # 纯内核，不需要装 VP
python tests/manual/test_e2e.py <any.vpp>                   # XML + Open API + 规格画图，约 1 分钟
python tests/manual/mcp_smoke.py <any.vpp>                  # MCP 协议 + 只读
```

前一组是 CI 跑的（27 个用例，16 ms），后两组需要真实安装，只操作临时副本。

## 9. 许可与边界

MIT。与 Visual Paradigm 官方无关：本工具驱动**已授权**的本地安装，不激活、不修改、
不再分发该产品。社区版的能力限制（XMI、代码生成等被门禁挡住）如实报 `edition-gated`，
不做绕过。

贡献方式见 `CONTRIBUTING.md`，安全问题见 `SECURITY.md`，版本记录见 `CHANGELOG.md`。


## 10. 踩坑（维护者笔记）

- VP 自带 JRE **没有 `jdk.zipfs`**：`javac -cp foo.jar` 报"没有任何文件系统提供程序处理文件"。
  先把 `openapi.jar` 解成目录再编译。
- 插件只认 `<pluginDir>/plugin.xml` + `<pluginDir>/lib/*.jar`；插件根的 jar 不进 classloader。
- `VPPlugin` 只有 `loaded(VPPluginInfo)` / `unloaded()`；命令行入口是 `VPPluginCommandLineSupport.invoke(String[])`。
- `-pluginargs` 按空格切分 → 脚本整体 base64 成单 token；回包用 stdout 的 `VPCE_RESP <base64>`。
- 18.1 的 `IProject` 没有 `getModel()` / `addChild()`；建元素靠
  `IModelElementFactory.instance().create(type)` + `DiagramManager.createDiagramElement()`，
  后者顺带把元素挂到工程根（新建图的 `getParentModel()` 是 null）。
- 新图形没有几何：必须 `setBounds` + `setRequestResetCaption(true)`，否则渲染出空框。
- 反射要落到**接口**的 Method：实现类多为包私有（`v.bgo.ctf`），直接 invoke 会 `IllegalAccessException`。
- 用独立 `APPDATA` 跑会停在 `License not found`（CE 许可在用户配置里），隔离测试跑不通。
