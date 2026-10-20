# ANOLISA Agent Entry

## 管控面 PoC（0.6）

顶栏 Agent 现在打开右上角的只读管控摘要；「查看详情」进入完整状态页，
「软件与安装」保留原应用目录。AW 区域不再点击启动 Qoder。
cosh 作为应用入口，运行视图计划由 herdr 支撑；当前只发现并启动已有 cosh 命令，
模式切换未实现。查看状态无需模型认证。
Hook 区域显示文件配置顺序、关闭/条件步骤和异常动作，不推断当前会话已接入。
热更新尚未接入；设计及试用边界见
[PoC 说明](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/agent-control-plane-poc.md)。


<!-- Modified 2026-10-17: documentation now follows the canonical Chinese README. -->

本插件文档以中文维护，完整说明见 [README.md](README.md)。本文件保留原型的中文文档入口。

当前版本 0.5.0；源码继承自 ANOLISA，采用 [Apache-2.0](LICENSE)，来源、固定提交和迁移改动见 [ORIGIN.md](ORIGIN.md)。

在仓库根目录运行 `./omarchy-tools aw`，一次完成预编译软件安装、面板部署与 AW 首次启动。详情见上面的完整说明。
