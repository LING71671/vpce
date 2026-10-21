# 架构：五层，依赖单向

```
cli.py / mcp_server.py   传输层：解析输入、格式化输出，不含业务判断
        |
service.py               用例层：编排 ports，不知道 argparse / JSON-RPC
        |
ports.py                 协议：Runtime / ProjectIO / Api
        |
adapters/                适配层：唯一碰 JVM、APPDATA、文件系统的地方
        |
core/                    内核：纯数据与纯函数，不 import 上面任何一层
```

硬规则（改代码前先看这里）：

| 规则 | 检查方式 |
|---|---|
| `core/` 只 import 标准库和自己 | `python -c "import vpce.core.spec"` 在没装 VP 的机器上也要能过 |
| `core/` 不启动进程、不读环境变量、不写文件 | 全文搜 `subprocess` / `os.environ` / `open(` 在 core 下应为 0 |
| `service.py` 只 import `core` 和 `ports` | 搜 `from .adapters` 应为 0 |
| 传输层不 import `adapters` | `cli.py` / `mcp_server.py` 只出现 `App` 与异常类型 |
| 适配层之间互不 import | 除 `api.py` 里的插件安装路径外，无交叉调用 |

## 各层职责

### core/ — 纯内核

| 模块 | 职责 |
|---|---|
| `errors.py` | 异常类型。适配层把控制台文本翻译成这里的具体异常 |
| `spec.py` | 画图规格的数据模型 + 校验（含 1455 个合法元素类型） |
| `layout.py` | 几何计算：layered / grid / usecase / radial / explicit |
| `profiles.py` | 每种图类型的默认布局与默认元素类型 |
| `program.py` | 规格 → Open API 语句。**唯一**知道建图配方的地方 |
| `model.py` | 解析 `project.xml`，只读视图 |
| `builder.py` | 生成 `ImportXML` 文档（XML 通道写入） |
| `model_types.json` | `IModelElementFactory` 的 1455 个 MODEL_TYPE 常量 |

### ports.py — 协议

三个 Protocol：`Runtime`（跑一条 VP 命令）、`ProjectIO`（读写一个工程）、`Api`（跑 Open API 语句）。
写测试时用假实现替换它们，不需要装 Visual Paradigm。

### adapters/ — 唯一的外部世界

| 模块 | 职责 |
|---|---|
| `runtime.py` | 找安装、拼 classpath、起 JVM、把控制台文本翻译成异常 |
| `workspace.py` | `ProjectIO` 实现：XML 导出/导入/渲染、缓存、备份、回读校验 |
| `api.py` | `Api` 实现：base64 传参、`VPCE_RESP` 回包、插件安装/卸载 |

### service.py — 用例

`ProjectService`（读/写/出图）、`DrawService`（规格 → 图 → 校验 → PNG）、`ApiService`（反射调用）。
只依赖构造时注入的 ports。

### cli.py / mcp_server.py — 传输

CLI 只做 argparse 与打印；MCP 只做 JSON-RPC 与错误映射。两者都通过 `App` 拿到 service。

## 加功能时的落点

| 想做的事 | 改哪里 |
|---|---|
| 支持一种新的排版（例如泳道） | `core/layout.py` 加一个函数 + `core/profiles.py` 指过去 |
| 让某类图默认用别的元素类型 | `core/profiles.py` 改一行 |
| 生成语句要带新属性（如可见性、颜色） | `core/spec.py` 加字段 + `core/program.py` 加一行 |
| 换一种传输（HTTP、WebSocket） | 新增一个 transport 文件，复用 `App`，其它层不动 |
| 换一个 VP 版本 | `adapters/runtime.py` 的候选路径与标记文本 |
| 不用插件、只走 XML | 只用 `ProjectService`，`DrawService` 不参与 |

## 数据流（draw）

```
spec.json
  → Spec.from_dict        校验类型/端点
  → layout.layout         按图类型画像排版，补 x/y/w/h
  → program.to_statements 生成 $am/$dm/$f/$d/$n0... 语句
  → adapters.api.run_script  base64 → com.vp.cmd.Plugin → 插件反射执行
  → adapters.workspace.verify_named  用 ExportXML 回读，独立代码路径确认落地
  → adapters.workspace.render        ExportDiagramImage 出 PNG
```
