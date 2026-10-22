# 让 AI 装

把下面这段丢给能执行命令的 AI。它跑通第 6 步就算装好。

## 提示词

````text
在这台机器上装 vpce：https://github.com/LING71671/vpce

1. 找 Visual Paradigm 安装目录（目录下同时有 lib/openapi.jar 和 bin/）
2. git clone 到你能写的目录，cd 进去
3. python -m venv .venv，激活，pip install -e .
4. python java/bridge/build.py
5. python -m vpce bridge --install
6. 复制任意 .vpp 到临时目录，然后：
   python -m vpce draw examples/order-system.json --project <副本路径> --out out/png

第 6 步能出 PNG 就算装好。哪一步报错就把报错原文贴给我，不要自己换参数试。
````

## 为什么是这几步

| 步骤 | 原因 |
|---|---|
| 用 VP 自带的 JDK 编译插件 | 它自带的 JRE 缺 `jdk.zipfs`，用系统 javac 编出来的字节码版本可能不匹配 |
| `bridge --install` | 插件要放进 `%APPDATA%\VisualParadigm\plugins\com.vpce.bridge`，VP 才认 |
| 用工程副本 | 写入会锁文件；副本坏了不影响原工程 |

## 装完之后

画图时换成这句：

```text
用 vpce 画一张 <类图/用例图/ER图>，内容是 <描述>。
写完先 --plan 看一眼语句，再落盘。
```

细节 AI 可以自己读 `skills/vpce-diagram-authoring/SKILL.md`。

## 耗时

| 步骤 | 时间 |
|---|---|
| clone + venv + pip | 1–2 分钟 |
| 编译插件 | 30–60 秒 |
| 装插件 | 1 秒 |
| 第 6 步 draw | 30–60 秒 |

单次调用 20–40 秒是正常的：每次都要起 JVM、初始化 VP、打开工程。
