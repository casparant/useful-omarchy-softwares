# ANOLISA Agent Entry

## 会话工作台 PoC（0.7）

顶栏 AW 提供紧凑摘要，详情显示真实会话、固定策略版本与运行代次。
cosh 是真正的 AI Shell；在其中运行 `aw run --agent qoder`，由 herdr 托管终端并经 AW 启动 Qoder。
关闭窗口后可返回同一活进程与对话；Panel 的“返回”不会新建 Agent。
安装后首次执行 `aw-session setup` 配置 herdr 官方 Qoder 身份 Hook。
“Hook 已绑定”来自存活进程、原生 Hook/binding 和在线 AW 实例的交叉核验；
不等于 API adoption 已验证或每次调用均获准。VM 重启续接和热更新未启用。
要求已安装 cosh、herdr、AW、Qoder，详见
[使用、证据与边界](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/agent-control-plane-poc.md)。

<!-- Modified 2026-10-17: documentation now follows the canonical Chinese README. -->

本插件文档以中文维护，完整说明见 [README.md](README.md)。本文件保留原型的中文文档入口。

当前版本 0.7.0；源码继承自 ANOLISA，采用 [Apache-2.0](LICENSE)，来源、固定提交和迁移改动见 [ORIGIN.md](ORIGIN.md)。

在仓库根目录运行 `./omarchy-tools aw`，一次完成预编译软件安装、面板部署与 AW 首次启动。详情见上面的完整说明。
