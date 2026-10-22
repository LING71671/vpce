# 图类型 × 元素类型（CE 18.1 实测）

来源：`E:\vpce\COVERAGE.md`，由 `tools/coverage.py --render` 生成。
每个"能出图"的条目都真的建过图、放进一个元素、存盘、渲染出 166x96 以上的 PNG。

## 29 个能画出来的

| 图类型 | 原生元素 | 布局 | 典型用途 |
|---|---|---|---|
| `ClassDiagram` | `Class` | layered | 领域模型、代码结构 |
| `ObjectDiagram` | `Object` | layered | 运行时快照 |
| `PackageDiagram` | `Package` | layered | 模块划分 |
| `ComponentDiagram` | `Component` | layered | 服务/组件依赖 |
| `DeploymentDiagram` | `Node`、`Artifact` | layered | 部署拓扑 |
| `CompositeStructureDiagram` | `Class`、`Component` | layered | 内部结构 |
| `ParametricDiagram` | `Class` | layered | SysML 约束 |
| `BlockDefinitionDiagram` | `Class` | layered | SysML 块定义 |
| `InternalBlockDiagram` | `Class` | layered | SysML 内部块 |
| `UseCaseDiagram` | `UseCase`（+`Actor`） | usecase | 需求场景 |
| `UseCaseDescriptionDiagram` | `UseCase` | usecase | 用例描述 |
| `ActivityDiagram` | `ActivityAction` | layered 纵向 | 业务流程 |
| `Flowchart` | `ActivityAction` | layered 纵向 | 算法流程 |
| `StateDiagram` | `State` | layered 纵向 | 状态机 |
| `InteractionDiagram` | `InteractionLifeLine` | grid | 时序 |
| `TimingDiagram` | `InteractionLifeLine` | grid | 时序波形 |
| `CommunicationDiagram` | `Actor` | grid | 协作 |
| `InteractionOverviewDiagram` | `Class` | layered | 交互概览 |
| `ERDiagram` | `DBTable`（列 `DBColumn`） | layered | 数据库设计 |
| `ChenNotationERD` | `ChenERDEntity` | layered | 概念 ER |
| `ORMDiagram` | `Class` | layered | ORM 映射 |
| `RequirementDiagram` | `Requirement` | grid | 需求追踪 |
| `EJBDiagram` | `Class` | layered | EJB 结构 |
| `FreehandDiagram` / `FreehandDiagram2` | `Class` | grid | 自由绘制 |
| `OverviewDiagram` | `Class` | grid | 总览 |
| `TextualAnalysis` | `Class` | grid | 文本分析 |
| `YourdonAndCoadDFD` | `Class` | layered | DFD |
| `YourdonDeMarcoDFD` | `Class` | layered | DFD |

## 2 个能建图但画不出内容

| 图类型 | 试过的元素 | 结果 |
|---|---|---|
| `CRCCardDiagram` | `CRCCard`、`Class` | 空图，伴随 NPE |
| `EAProcessStepDiagram` | `EAProcessStep`、`ActivityAction`、`Class` | 空图 |

结论：编辑器型画布，不接受模型元素形状。**不要在这两个上花时间。**

## 75 个该版本不支持的

调用 `createDiagram` 直接抛 `UnsupportedOperationException: <类型> is not supported`：

```
ActorGridDiagram AnalysisDiagram AnalysisItemDiagram ArchiMate4Diagram ArchiMateDiagram
ArchitectureRoadmap Brainstorm BreakdownStructure BusinessMotivationModelDiagram
BusinessProcessDiagram BusinessProcessReengineering BusinessRuleEditorDiagram
BusinessRuleGridDiagram C4modelComponentDiagram C4modelContainerDiagram
C4modelDeploymentDiagram C4modelDynamicDiagram C4modelSystemContextDiagram
C4modelSystemLandscapeDiagram CMMNDiagram ChartDiagram CompetitorAnalysis
ConversationDiagram CustomerJourneyMap DTBDecisionTableEditorDiagram DataFlowDiagram
DataStudioSheet DataTableDiagram DecisionModelDiagram DocumentationCabinet
EAFormDiagram EPCDiagram ETLTableDiagram FactDiagram FactTypeEditorDiagram FishboneDiagram
Form GaneSarsonDFD GlossaryGridDiagram GridDiagram MatrixDiagram MaturityAnalysis
MigrationRoadmap MindMapDiagram OrganizationChart PERTChart PMProcessMap ProcessCanvas
ProcessMapDiagram ProfileDiagram QualityControlCanvas ReportDiagram RequirementGridDiagram
RootCauseAnalysis SoaMLServiceCategorizationDiagram SoaMLServiceContractDiagram
SoaMLServiceInterfaceDiagram SoaMLServiceParticipantDiagram SoaMLServicesArchitectureDiagram
Tabular TermEditorDiagram UseCaseGridDiagram UserInterfaceDiagram UserStoryMapDiagram
ViewEditorDiagram WFAndroidPhoneDiagram WFAndroidTabletDiagram WFDesktopDiagram
WFIPadDiagram WFIPhoneDiagram WFWebDiagram WSDLDiagram WebDiagram WireflowDiagram
ZachmanDiagram
```

常见误会：**`MindMapDiagram`、`DataFlowDiagram`、`C4model*`、`Brainstorm`、`Wireflow` 在这个
CE 版本都画不了**，用户点名要的时候直接说明，别硬试。

## 元素类型清单

1455 个合法名字在 `E:\vpce\vpce\core\model_types.json`。
四个只能用父节点造：`Sprint`、`UseCaseStatement`、`UserStory`、`UserStoryConfirmation`
（`create()` 拒绝，`createChild()` 通过）——`vpce draw` 走的是 `create()`，遇到这四个要改用
`vpce api` 手写 `createChild`。
