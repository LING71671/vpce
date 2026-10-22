# `vpce api`：规格之外的逃生口

规格能表达的只是"节点 + 边 + 布局"。凡是规格没有的（改属性、批量、读状态、自定义关系名），
用 `vpce api` 直接写 Open API 语句。

```bash
python -m vpce api <project.vpp> '语句1' '语句2' ...
python -m vpce api <project.vpp> --file script.vpce
```

## 表达式语言

| 写法 | 含义 |
|---|---|
| `ApplicationManager.instance()` | 静态/实例方法调用 |
| `$x = 表达式` | 存变量，后续用 `$x` |
| `$d.getName` | 无参方法可省略括号 |
| `"字符串"` / `123` / `true` / `null` | 字面量 |
| `DiagramTypeConstants.UML_CLASS_DIAGRAM` | 静态常量（`CLASS.CONSTANT` 形式自动解析） |
| `$arr.length` / `$arr.get(2)` | 数组长度与下标 |
| `@introspect <类名>` | 列方法与静态常量 |
| `@search <片段>` | 在 classpath 里找类 |

类名可以写简名（`IDiagram`、`IProject`、`IModelElementFactory`），解析器会自动加
`com.vp.plugin.*` 等前缀，最后再按简名索引兜底。

返回值会打成 `r3 = String xxx` 或 `error#3 java.lang.XxxException: ...`。**异常会剥到根因**，
所以 `UnsupportedOperationException: X is not supported` 这种能直接看到。

## 已验证配方

### 建图 + 建元素 + 定位（`vpce draw` 内部就是这套）

```
$am = ApplicationManager.instance()
$dm = $am.getDiagramManager()
$f  = IModelElementFactory.instance()
$d  = $dm.createDiagram("ClassDiagram")
$d.setName("Demo")
$e  = $f.create("Class")
$e.setName("Order")
$a  = $e.createChild("Attribute")
$a.setName("total")
$a.setType("double")
$s  = $dm.createDiagramElement($d, $e)
$s.setBounds(60, 40, 170, 90)
$s.setRequestResetCaption(true)
$am.getProjectManager().saveProject()
```

三个坑都在这里：`createDiagramElement` 顺带把元素挂到工程根；**不 `setBounds` 就是空框**；
**不 `setRequestResetCaption(true)` 类名不显示**。

### 连线

```
$r  = $f.create("Association")
$r.setName("places")
$r.setFrom($e1)
$r.setTo($e2)
$dm.createConnector($d, $r, $s1, $s2, null)
```

第 5 个参数是 `java.awt.Point[]` 走线点；传 `null` 让 VP 走直线。

### 读状态

```
$am = ApplicationManager.instance()
$p = $am.getProjectManager().getProject()
$p.toDiagramArray().length
$p.toModelElementArray("Class").length
$p.getDiagramById("<id>").getName()
```

注意：18.1 的 `IProject` **没有** `getModel()` / `addChild()`。读用 `toModelElementArray()`、
`allLevelModelElementIterator()`；写用 `createDiagramElement()`。

### 造 `create()` 拒绝的类型

```
$f = IModelElementFactory.instance()
$pkg = $f.create("Package")
$pkg.setName("holder")
$us = $pkg.createChild("UserStory")
$us.setName("As a user I want...")
```

## 探路顺序

1. `@search <关键词>` 找类（只扫 `com.vp.plugin.**`）
2. `@introspect <类>` 看方法与静态常量（常量会打印实际值，`DiagramTypeConstants` 就是这么来的）
3. 小脚本试一个调用，看返回类型
4. 拼进完整脚本

不要凭记忆写 VP 的 API 名字——同一份 SDK 里 `Lifeline` 其实叫 `InteractionLifeLine`，
`Column` 在 ERD 里叫 `DBColumn`。

## 限制

- 脚本整体 base64 后走 `-pluginargs`（因为参数按空格切分），**太长会撞命令行长度上限**，
  大批量请分批。
- 每次调用起一个 JVM，7–10 秒；批量操作合并成一个脚本。
- 工程被 GUI 打开时写入会失败（`Project file locked`）。
