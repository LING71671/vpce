# 让 AI 自己装（复制粘贴用）

把下面整段丢给任意能执行命令的 AI（Claude Code / Cursor / Codex / WorkBuddy），它会自己
完成安装、编译插件、验证，并把结果汇报成一张表。不需要你逐步指挥。

前提：这台机器上**已经装了 Visual Paradigm**（社区版即可），并且 AI 有执行 shell 的权限。

---

## 中文提示词

````text
帮我在这台机器上安装 vpce（https://github.com/LING71671/vpce），然后验证它能用。

按顺序做，每步失败就停下来告诉我原因，不要跳过：

1. 找 Visual Paradigm 安装目录。特征：目录下同时有 lib/openapi.jar 和 bin/。
   常见位置 C:\Program Files\Visual Paradigm*、D:\、E:\ 根目录，
   也可能是别的盘。找不到就问我。

2. 把仓库 clone 到合适的位置（不要放在需要管理员权限的目录），进目录后执行：
   python -m venv .venv，激活它，然后 pip install -e .

3. 用 Visual Paradigm 自带的 JDK 编译桥插件：
   python java/bridge/build.py
   如果报「没有任何文件系统提供程序处理文件」，说明脚本没走到解包那步，
   把错误原文发我，别自己改 javac 参数。

4. 装插件并确认状态：
   python -m vpce bridge --install
   python -m vpce bridge
   要求输出里 installed 为 true。如果 APPDATA 不可写，告诉我，不要动系统目录。

5. 跑只读检查：
   python -m vpce status --probe
   把哪些命令是 available、哪些是 edition-gated 列出来。这一步要起几次 JVM，
   单次 20-40 秒是正常的，不要以为卡住了。

6. 端到端验证：复制一份任意 .vpp 到临时目录（不要用原文件），然后
   python -m vpce draw examples/order-system.json --project <副本> --out <临时目录>/png
   要求 verify.elements_missing 和 verify.diagrams_missing 都是空，
   并且 png 目录里有非空的 PNG。

7. 最后汇报成表：安装路径、Python 版本、桥插件状态、可执行/被门禁的命令数、
   生成的 PNG 路径。有任何一步没通过，明确写出来，不要含糊。

约束：
- 不要修改用户已有的 .vpp 工程，只操作临时副本。
- 不要为了绕过 edition-gated 的命令去改程序或找破解，那部分能力就是没有。
- 不要 pip install 到全局环境，用 venv。
````

## English prompt

````text
Install vpce (https://github.com/LING71671/vpce) on this machine and prove it works.

Work through these steps in order. If a step fails, stop and tell me why — do not skip.

1. Locate the Visual Paradigm installation: the directory containing both
   lib/openapi.jar and bin/. Check C:\Program Files\Visual Paradigm*, drive
   roots such as D:\ and E:\. Ask me if you cannot find it.

2. Clone the repository somewhere writable, then:
   python -m venv .venv && activate && pip install -e .

3. Build the bridge plugin with the JDK that ships with Visual Paradigm:
   python java/bridge/build.py
   If it fails with "no file system provider handles file", send me the exact
   error instead of changing the javac flags yourself.

4. Install the plugin and check it:
   python -m vpce bridge --install
   python -m vpce bridge
   `installed` must be true. If %APPDATA% is not writable, tell me — do not
   touch system directories.

5. Run the read-only probe:
   python -m vpce status --probe
   List which commands are available and which are edition-gated. Each probe
   starts a JVM; 20-40 s per call is normal, not a hang.

6. End-to-end check: copy any .vpp to a temp directory (never the original), then
   python -m vpce draw examples/order-system.json --project <copy> --out <tmp>/png
   `verify.elements_missing` and `verify.diagrams_missing` must be empty and the
   PNG must be non-empty.

7. Report a table: install path, Python version, bridge status, executable vs
   gated command counts, PNG path. State any failed step plainly.

Rules:
- Never write to the user's existing .vpp files; work on temp copies.
- Do not try to get around edition-gated commands. That capability is simply
  not in the Community Edition.
- No global pip installs; use the venv.
````

---

## 装完之后让它画图

安装只是第一步。真正画图时把那句提示词换成：

```text
用 vpce 画一张 <类图/用例图/ER图/...>，内容是 <描述>。
先看 skills/vpce-diagram-authoring/references/diagram-recipes.md 确认图类型和元素类型，
写 spec 后先 --plan 检查，再落盘，最后把 PNG 打开看一眼再汇报。
```

`skills/vpce-diagram-authoring/SKILL.md` 是完整的作业说明，AI 可以直接读。

## 给 AI 的预期耗时

| 步骤 | 时间 |
|---|---|
| clone + venv + pip install | 1–2 分钟 |
| 编译插件（首次解包 openapi.jar） | 30–60 秒 |
| 装插件 | 1 秒 |
| `status --probe` | 2–4 分钟（每个命令一次 JVM） |
| 端到端 draw | 30–60 秒 |

如果 AI 报「每次调用都很慢」，那是正常的：单次调用要起 JVM、初始化 Visual Paradigm、
打开工程，20–40 秒。批量查询请合并成一次调用。
