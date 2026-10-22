# 踩坑笔记（维护者）

这些是写这个工具时必须先知道的事，全部来自实测。改代码前读一遍能省掉几小时。

## 构建

### VP 自带 JRE 没有 `jdk.zipfs`

```
javac -cp openapi.jar ...
错误: 没有任何文件系统提供程序处理文件: .../openapi.jar
```

`jdk.compiler` 在，`jdk.zipfs` 不在——所以 `javac` 读不了 jar 形式的 classpath。
解法：先把 `openapi.jar` 解成目录，再 `-cp <目录>`。`java/bridge/build.py` 就是这么做的。

顺带：没有 `javap`，反查接口用 `tools/classdump.py`（直接解析 .class 的常量池与方法表）。

### 插件目录结构是硬约束

只认 `<pluginDir>/plugin.xml` + `<pluginDir>/lib/*.jar`。

- 加载器只扫插件目录下的 `classes/` 和 `lib/` 两个子目录
- 直接放在插件根的 jar **不会**进 classloader，表现为 `ClassNotFoundException: vpce.bridge.Bridge`
- `plugin.xml` 最小集：`<plugin id name provider version description class>`
- 插件目录固定 `%APPDATA%\VisualParadigm\plugins\<pluginId>\`

### `VPPlugin` 只有两个方法

```java
void loaded(VPPluginInfo info);
void unloaded();
```

命令行入口是另一个接口 `VPPluginCommandLineSupport.invoke(String[])`。
`VPPluginInfo` 只给 `getPluginId()` 和 `getPluginDir()`。

## 传参

### `-pluginargs` 按空格切分

`-pluginargs "a b c"` 到插件里是 `String[]{"a","b","c"}`。所以脚本整体 base64 成一个
token 传进去，回包用 stdout 的 `VPCE_RESP <base64>` 单行输出。副作用：脚本原文超过约
20KB 会撞 Windows 命令行 32K 上限，要分批。

### 异常要剥到根因

反射调用抛的是 `InvocationTargetException`，直接打印只能看到 `null`。
不剥壳就永远看不到真正有用的那句 `UnsupportedOperationException: X is not supported`。

## 模型操作

### 18.1 的 `IProject` 没有 `getModel()` / `addChild()`

老文档和大量示例里的 `getProject().getModel()` 在这个版本不存在。实际做法：

- 读：`toModelElementArray(type)`、`allLevelModelElementIterator()`、`getModelElementById(id)`
- 写：`IModelElementFactory.instance().create(type)` +
  `DiagramManager.createDiagramElement(diagram, element)`

`createDiagramElement` 会**顺带把模型元素挂到工程根**——新建图的 `getParentModel()` 是
`null`，别试图先找根节点再 `addChild`。

### 新图形没有几何

`createDiagramElement` 返回的形状宽高是 0。必须：

```java
shape.setBounds(x, y, w, h);
shape.setRequestResetCaption(true);   // 少了这句，类名不显示
```

否则导出的图是空框（或 4x4 像素）。

### 反射要落到接口的 Method

VP 的实现类基本是包私有的（`v.bgo.ctf`、`v.bgg.d`）。在实现类上 `getMethods()` 再
`invoke` 会 `IllegalAccessException`。要沿 `getInterfaces()` 递归收集公开方法，
拿到接口上那份 `Method` 再调用。

### 四个类型只能 `createChild()`

`Sprint`、`UseCaseStatement`、`UserStory`、`UserStoryConfirmation`：`create()` 抛
`Cannot create X`，但从一个 `Package` 上 `createChild()` 可以。

## 测量

### 「能 create」≠「能渲染」

同一图类型下，工厂接受的元素类型不一定画出形状：

| 图类型 | 空图 | 能画 |
|---|---|---|
| `ActivityDiagram` / `Flowchart` | `Action` | `ActivityAction` |
| `ObjectDiagram` | `Object` | `Class` |
| `CommunicationDiagram` | `Object` | `Actor` |

别凭直觉填 `node_type`，用 `tools/find_shapes.py` 跑一遍。

### 两个图类型根本放不进元素

`CRCCardDiagram`、`EAProcessStepDiagram`：编辑型画布，原生元素 / `Class` 兜底 /
专属元素（`CRCCard`）全试过，一律空图并伴随 NPE。

### 环境隔离会撞许可

用独立 `APPDATA` 跑（想把配置隔离到工作目录）会停在 `License not found`——
CE 的社区许可存在用户配置里，所以隔离测试跑不通，必须用真实配置。

## 未解决：ER 图的列在无头导出里画不出来

现象：`vpce draw` 建的 ER 图，表框只有表名，没有列；用 GUI 打开能看到列。

已排除（都是实测）：

| 假设 | 结论 |
|---|---|
| 无头导出本身不支持 | **否**。把 GUI 建的 exercise2.vpp 复制出来无头导出，列、主键图标、FK 全都在 |
| 模型缺列 | **否**。导出的 XML 里 `DBTable/ModelChildren` 有两个 `DBColumn`，属性与 GUI 建的逐字段一致 |
| 形状属性不同 | **否**。GUI 与生成的 `<DBTable>` 形状，属性集合与子元素完全一致，只有几何值不同 |
| 图级别开关（`_showColumnTypes` 等） | **部分是**。在已有 ER 图的老工程里新建表，列**能画出来**（只是位置贴在框底）；在没有任何 ER 图史的新工程里建，列为空 |
| `setShowColumnsMode` | 无效。0（跟随图）和 1（全显示）渲染结果一样 |
| `setRequestFitSize(true)` | **更糟**。会把框缩到只剩表名（6x6 内容） |
| 复制图 API | 不存在，`DiagramManager` 只有 `createDiagram(String)` |

当前可用做法（有实测支撑）：

- 目标工程里**已经有一个 GUI 建的 ER 图**时，`vpce draw` 新建的表能画出列，
  但行会压在框底，需要给足高度并手工微调。
- 全新工程里直接建 ER 图，列不出现。

下一步要查的方向：表形状的 caption 尺寸（GUI 是 `@width=220,@height=16,@side=12`，
生成的是 `0/0/0`）与列行起始位置的关系；以及 `IDiagramUIModel` 的图属性只有 getter
（`IDiagramProperty` 没有 setter），图级开关要么靠导入时继承，要么得另找入口。

`tools/probe_erd_*.py` 是这轮留下的探针，别删。
