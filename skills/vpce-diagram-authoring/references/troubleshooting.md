# 报错 → 处置

全部来自 CE 18.1 实测。

## 环境

| 现象 | 原因 | 处置 |
|---|---|---|
| `Visual Paradigm not found` | 没找到安装 | `--vp-home "E:\Visual Paradigm CE 18.1"` 或设 `VPCE_HOME` |
| `bridge plugin not installed` | 插件没装 | `python -m vpce bridge --install`（要先 `python java/bridge/build.py`） |
| `bridge class failed to load` | 插件目录结构不对 | 必须是 `<plugins>\<id>\plugin.xml` + `lib\*.jar`；根目录下的 jar 不生效 |
| `bridge plugin not built` | 没编译 | `python java/bridge/build.py` |

## 工程

| 现象 | 原因 | 处置 |
|---|---|---|
| `Project file locked` | GUI 打开着同一个工程 | 关掉 GUI 或换副本 |
| `project needs -upgrade-project` | 工程是旧版本文件 | `python -m vpce upgrade <project>`（会先备份） |
| `project not found` | 路径错 | 用绝对路径 |

## 画图

| 现象 | 原因 | 处置 |
|---|---|---|
| `unknown element type 'X'; did you mean ...` | 元素类型名不对 | 按建议改名；名字必须在 `model_types.json` 里 |
| `edge endpoint 'x' is not a node id` | 边的端点没定义 | 先加节点，`id` 要一致 |
| `self-loop on 'x' is not supported yet` | 起止同节点 | 拆成两条边，或改用 `vpce api` 手写 |
| `unknown diagram type` / `is not supported` | 该版本不支持这个图类型 | 换图类型；名单见 `diagram-recipes.md` |
| 建图成功但 PNG 是 4x4 / 0x0 | 元素类型在该图里不落地 | 换回表里的原生元素；仍不行说明是编辑器型图 |
| 图里有框但没名字 | 少了 caption 刷新 | 用 `vpce api` 补 `$s.setRequestResetCaption(true)` |
| 元素全叠在左上角 | 没给坐标也没走画像 | 检查 `layout.mode`；`explicit` 必须给 `x/y` |
| 连线穿过别的图元 | VP 默认直线路由 | 换 `grid`/`layered` 减少共线，或 `vpce api` 传走线点 |

## 版本门禁

```
Feature not supported by current edition
```

这条命令该版本不给用（XMI、Excel、BPMN、代码生成、报表、`InstantReverse` 都属此类）。
**不要重试、不要想办法绕过**，直接换方案或告知用户需要付费版本。

## 调试手法

```bash
python -m vpce draw spec.json --project p.vpp --plan      # 只排版，看有没有类型错误
python -m vpce draw spec.json --project p.vpp --script    # 看实际下发的语句
python -m vpce summary p.vpp --refresh                    # 元素数/图数对不对
python -m vpce diagrams p.vpp --text                      # 图里 shapes/connectors 计数
python -m vpce images p.vpp --out /tmp/png --diagram 名字  # 单独渲染一张
```

`diagrams --text` 里 `shapes=0` 就是没落进元素，`connectors=0` 就是边没建上。
