# 覆盖率台账

> 由 `python tools/coverage.py <project> --render` 实测生成，只反映**上一次运行**。
> 不要手改本文件。

环境：`E:\Visual Paradigm CE 18.1`

## 汇总

| 维度 | 通过 | 分母 | 比例 | 说明 |
|---|---|---|---|---|
| 图类型可创建 | 31 | 106 | 29.2% | 其余 75 个是产品侧 `is not supported` |
| 图类型可出图 | 29 | 31 | 93.5% | 分母为受支持类型；能放入元素并渲染出非空 PNG |
| 其中用原生元素 | 29 | 31 | 93.5% | 其余靠 `Class` 兜底，配图语义未必正确 |
| 元素类型可创建 | 1455 | 1455 | 100.0% | 含 4 个只能经 `createChild` 构造 |
| 命令行可执行 | 11 | 28 | 39.3% | 其余被版本门禁挡住 |

## 端到端出图

| 图类型 | 元素类型 | 方式 | 尺寸 |
|---|---|---|---|
| ActivityDiagram | ActivityAction | 原生 | 166x96 |
| BlockDefinitionDiagram | Class | 原生 | 166x96 |
| CRCCardDiagram | Class | 原生 | 0x0 |
| ChenNotationERD | ChenERDEntity | 原生 | 166x96 |
| ClassDiagram | Class | 原生 | 166x96 |
| CommunicationDiagram | Actor | 原生 | 166x112 |
| ComponentDiagram | Component | 原生 | 166x96 |
| CompositeStructureDiagram | Class | 原生 | 166x96 |
| DeploymentDiagram | Node | 原生 | 166x96 |
| EAProcessStepDiagram | Class | 原生 | 0x0 |
| EJBDiagram | Class | 原生 | 166x96 |
| ERDiagram | DBTable | 原生 | 166x96 |
| Flowchart | ActivityAction | 原生 | 166x96 |
| FreehandDiagram | Class | 原生 | 166x96 |
| FreehandDiagram2 | Class | 原生 | 166x96 |
| InteractionDiagram | InteractionLifeLine | 原生 | 166x96 |
| InteractionOverviewDiagram | Class | 原生 | 166x96 |
| InternalBlockDiagram | Class | 原生 | 166x112 |
| ORMDiagram | Class | 原生 | 166x96 |
| ObjectDiagram | Object | 原生 | 166x96 |
| OverviewDiagram | Class | 原生 | 166x96 |
| PackageDiagram | Package | 原生 | 166x96 |
| ParametricDiagram | Class | 原生 | 166x96 |
| RequirementDiagram | Requirement | 原生 | 166x96 |
| StateDiagram | State | 原生 | 166x96 |
| TextualAnalysis | Class | 原生 | 166x96 |
| TimingDiagram | InteractionLifeLine | 原生 | 166x96 |
| UseCaseDescriptionDiagram | UseCase | 原生 | 166x96 |
| UseCaseDiagram | UseCase | 原生 | 166x96 |
| YourdonAndCoadDFD | Class | 原生 | 166x112 |
| YourdonDeMarcoDFD | Class | 原生 | 166x96 |

## 图类型（106）

- 可创建：**31**
- 产品侧不支持：**75**（`UnsupportedOperationException: <类型> is not supported`）

`ActorGridDiagram`、`AnalysisDiagram`、`AnalysisItemDiagram`、`ArchiMate4Diagram`、`ArchiMateDiagram`、`ArchitectureRoadmap`、`Brainstorm`、`BreakdownStructure`、`BusinessMotivationModelDiagram`、`BusinessProcessDiagram`、`BusinessProcessReengineering`、`BusinessRuleEditorDiagram`、`BusinessRuleGridDiagram`、`C4modelComponentDiagram`、`C4modelContainerDiagram`、`C4modelDeploymentDiagram`、`C4modelDynamicDiagram`、`C4modelSystemContextDiagram`、`C4modelSystemLandscapeDiagram`、`CMMNDiagram`、`ChartDiagram`、`CompetitorAnalysis`、`ConversationDiagram`、`CustomerJourneyMap`、`DTBDecisionTableEditorDiagram`、`DataFlowDiagram`、`DataStudioSheet`、`DataTableDiagram`、`DecisionModelDiagram`、`DocumentationCabinet`、`EAFormDiagram`、`EPCDiagram`、`ETLTableDiagram`、`FactDiagram`、`FactTypeEditorDiagram`、`FishboneDiagram`、`Form`、`GaneSarsonDFD`、`GlossaryGridDiagram`、`GridDiagram`、`MatrixDiagram`、`MaturityAnalysis`、`MigrationRoadmap`、`MindMapDiagram`、`OrganizationChart`、`PERTChart`、`PMProcessMap`、`ProcessCanvas`、`ProcessMapDiagram`、`ProfileDiagram`、`QualityControlCanvas`、`ReportDiagram`、`RequirementGridDiagram`、`RootCauseAnalysis`、`SoaMLServiceCategorizationDiagram`、`SoaMLServiceContractDiagram`、`SoaMLServiceInterfaceDiagram`、`SoaMLServiceParticipantDiagram`、`SoaMLServicesArchitectureDiagram`、`Tabular`、`TermEditorDiagram`、`UseCaseGridDiagram`、`UserInterfaceDiagram`、`UserStoryMapDiagram`、`ViewEditorDiagram`、`WFAndroidPhoneDiagram`、`WFAndroidTabletDiagram`、`WFDesktopDiagram`、`WFIPadDiagram`、`WFIPhoneDiagram`、`WFWebDiagram`、`WSDLDiagram`、`WebDiagram`、`WireflowDiagram`、`ZachmanDiagram`

## 能建图但放不进元素（编辑器型）

`CRCCardDiagram`、`EAProcessStepDiagram`

## 元素类型（1455）

- 可直接 `create()`：**1451**
- 需经 `createChild()`：**4**（`Sprint`、`UseCaseStatement`、`UserStory`、`UserStoryConfirmation`）
- 仍然失败：**0**

## 命令行门禁

| 命令 | 状态 |
|---|---|
| CommitTeamworkProject | 可执行 |
| CompactVPServerProjectFolder | 可执行 |
| DetectJavaFX | 可执行 |
| ExitCode | 可执行 |
| ExportBPMN | 被版本门禁挡住 |
| ExportDiagramImage | 可执行 |
| ExportDocComposer | 被版本门禁挡住 |
| ExportExcel | 被版本门禁挡住 |
| ExportXMI | 被版本门禁挡住 |
| ExportXML | 可执行 |
| GenerateDocument | 被版本门禁挡住 |
| GenerateORM | 被版本门禁挡住 |
| GenerateReport | 被版本门禁挡住 |
| ImportBPMN | 被版本门禁挡住 |
| ImportExcel | 被版本门禁挡住 |
| ImportXMI | 被版本门禁挡住 |
| ImportXML | 可执行 |
| InstantGenerator | 被版本门禁挡住 |
| InstantReverse | 被版本门禁挡住 |
| InstantReverseSD | 被版本门禁挡住 |
| JavaCodeSync | 被版本门禁挡住 |
| Plugin | 可执行 |
| ProjectPublisher | 被版本门禁挡住 |
| RegisterUrlScheme | 可执行 |
| ReverseDDL | 被版本门禁挡住 |
| ReverseHibernate | 被版本门禁挡住 |
| TWKActionServiceCommandLineImpl | 可执行 |
| UpdateTeamworkProject | 可执行 |

## 复现

```bash
python java/bridge/build.py
python -m vpce bridge --install
python tools/dump_diagram_types.py <any.vpp>
python tools/coverage.py <any.vpp> --render
python tools/find_shapes.py <any.vpp>      # 找每个图类型的可用元素
```
