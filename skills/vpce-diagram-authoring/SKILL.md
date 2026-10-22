---
name: vpce-diagram-authoring
description: >
  用 vpce 在 Visual Paradigm 里画 UML / ER / 流程图等图：写一份 JSON 规格，工具负责建模型、
  建图、连线、排版、存盘、导出 PNG，全程无 GUI 无人工。当用户说"画个类图/用例图/活动图/状态图/
  ER图/部署图/组件图/时序图/包图/需求图"、"用 Visual Paradigm 画"、"把这段设计画成图"、
  "生成 UML"、"画出架构图"、"vpce draw"，或提到 vpce / Visual Paradigm / vpp / .vpp 文件时使用。
  Use when asked to draw UML, ER, activity, state, component, deployment, use case or requirement
  diagrams with Visual Paradigm through vpce, or to author a diagram spec programmatically.
agent_created: true
---

# 用 vpce 画图

规格驱动：**你只产出 JSON，工具负责在真实 Visual Paradigm 里建模型、落图、存盘、出图。**

```
spec.json ──vpce draw──► .vpp 工程 + PNG + 回读校验
```

## 0. 先确认环境（缺一步就别往下写规格）

命令都要在仓库根目录（`E:\vpce`）执行，或先 `pip install -e .`。
下文的 `spec.json`、`copy.vpp` 都指你自己建的临时文件。

```bash
python -m vpce status                       # 能找到安装、有多少命令
python -m vpce bridge                       # installed 必须是 true
```

- `bridge.installed == false` → `python -m vpce bridge --install`
  （插件没装就只能走 XML 通道，画不了连线和新图）
- 报 `Project file locked` → 让用户关掉 GUI 里打开的工程，重试
- 报 `edition-gated` → 这条命令该版本不给用，换方案，不要重试

工程文件必须是**副本**：先在临时目录拷一份 `.vpp`，不要直接改用户的工程。

## 1. 选型（照这张表，别猜）

受支持且能出图的图类型 **29 个**，每个都有验证过的原生元素类型：

| 图类型 `diagram` | 节点默认 `type` | 常见关系 `edges[].type` |
|---|---|---|
| `ClassDiagram` | `Class` | Association / Generalization / Dependency |
| `UseCaseDiagram` | `UseCase`（角色用 `Actor`） | Association / Include / Extend |
| `ActivityDiagram` | `ActivityAction` | ControlFlow |
| `StateDiagram` | `State` | Transition |
| `Flowchart` | `ActivityAction` | ControlFlow |
| `ERDiagram` | `DBTable`（列用 `DBColumn`） | Association |
| `ChenNotationERD` | `ChenERDEntity` | ChenERDRelationship |
| `ComponentDiagram` | `Component` | Dependency |
| `DeploymentDiagram` | `Node` / `Artifact` | Association |
| `PackageDiagram` | `Package` | Dependency |
| `ObjectDiagram` | `Object` | Association |
| `CommunicationDiagram` | `Actor` | Association |
| `InteractionDiagram` / `TimingDiagram` | `InteractionLifeLine` | Message |
| `CompositeStructureDiagram` | `Class` / `Component` | Association |
| `RequirementDiagram` | `Requirement` | Association |

完整 29 个 + 每个的实测尺寸见 `references/diagram-recipes.md`。

**不要碰**这 2 个：`CRCCardDiagram`、`EAProcessStepDiagram` —— 能建图但放不进元素，一定是空图。
另有 75 个图类型这个 CE 版本直接 `is not supported`，名单在 references 里。

元素类型不是随便填的：工厂认 1455 个名字，写错会报
`unknown element type 'X'; did you mean ...`。拿不准就查：

```bash
python -m vpce search <project> Diagram DBTable DBColumn   # 多个词一次查
python -m vpce introspect <project> IDBTable IDBColumn     # 多个类一次查
```

**探查要合并成一次调用。** 每次 `vpce` 调用都要起 JVM、初始化 VP、打开工程，
实测单次 20–40 秒——一个类一次调用会让你等两分钟。规则：

- 一次给全：`introspect A B C`、`vp_api_introspect` 用 `class_names` 数组
- 同样的问题重复问会走缓存（约 1 秒），但**第一次仍然要 30 秒**，所以先想清楚要查什么
- 能靠 `references/diagram-recipes.md` 里的表回答的，就别去探 API

## 2. 写规格

最小可画：

```json
{
  "diagram": "ClassDiagram",
  "name": "Order System",
  "nodes": [
    {"id": "customer", "type": "Class", "name": "Customer",
     "attributes": ["id:long", "email:string"], "operations": ["placeOrder"]},
    {"id": "order", "type": "Class", "name": "Order", "attributes": ["total:double"]}
  ],
  "edges": [{"from": "customer", "to": "order", "type": "Association", "name": "places"}]
}
```

规则：

- `id` 只用于连边，不会显示在图里；`name` 才是图上的文字。
- `attributes` 写 `"名字:类型"`；`operations` 只写名字，VP 自己补括号。
- `layout.mode` 不写就用该图类型的默认画像（类图 layered、用例图 actors 靠左、活动/状态纵向、思维导图 radial）。要覆盖再显式写 `grid` / `layered` / `usecase` / `radial` / `explicit`。
- 需要精确位置时逐个给 `x/y/width/height`，配 `"mode": "explicit"`。
- 一份规格一张图。多张图就写多份，各自 `draw`。

## 3. 先 `--plan` 再落盘

```bash
python -m vpce draw spec.json --project /tmp/copy.vpp --plan      # 只排版+生成语句，不写工程
python -m vpce draw spec.json --project /tmp/copy.vpp --out png/  # 真画
```

`--plan` 能提前抓到类型写错、边端点不存在、id 重复。`--script` 会打印实际下发的语句，
排查"为什么长得不对"时先看它。

## 4. 验收（必做，别只看命令返回 0）

`draw` 的输出里已经有：

- `verify.elements_missing` / `verify.diagrams_missing` 必须都是空的
- `images[].bytes` 要有几 KB；`px` 太小（< 60x40）说明图是空的
- **打开 PNG 看一眼**。数字对不代表图对：元素挤成一列、连线穿过别的图元都是常见结果。

## 5. 画不成时

| 现象 | 处置 |
|---|---|
| `unknown element type` | 按提示改用建议名；`Lifeline`→`InteractionLifeLine`、`Column`→`DBColumn` |
| 图能建但 PNG 空 | 该类型不接受这个元素；换回表里的原生类型 |
| `is not supported` | 该版本不支持这个图类型，换图类型，不要重试 |
| `Project file locked` | 关 GUI 或换副本 |
| 元素重叠/连线穿图 | 调 `layout`（`grid` 换列数、`layered` 改纵向）或直接给 `x/y` |

更多见 `references/troubleshooting.md`。

## 6. 规格表达不了的时候

用 `vpce api` 直接调 Open API（逃生口），表达式一行一句、`$x = ...` 存变量：

```bash
python -m vpce api copy.vpp \
  '$am = ApplicationManager.instance()' \
  '$p = $am.getProjectManager().getProject()' \
  '$p.toDiagramArray().length'
```

已验证的配方（连线、改属性、批量保存、读布局）在 `references/api-escape-hatch.md`。

## 输出给用户时

- 报图类型、元素数、关系数，以及 PNG 路径。
- 说明用了原生元素还是兜底；兜底（`Class` 放进非类图）要讲清楚语义可能不对。
- 不要宣称"支持所有图"：这个 CE 版本 106 个图类型里只有 31 个能建、29 个能画出内容。
