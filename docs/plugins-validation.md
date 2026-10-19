# Agent Entry 验证记录

当前版本 0.3.0，保留 `anolisa.agent-entry` ID。公开源码来源、固定提交与 Apache-2.0 声明见 [ORIGIN](../plugins/agent-entry/ORIGIN.md)。验证环境为 Darwin arm64 / Python 3.9.6；未在目标 Omarchy 桌面部署。

## 2026-10-19 · 0.3.0 双语

- 新增英语 / 中文界面和 `language: auto|en|zh` 持久化选择。系统语言按 `LC_ALL`、`LC_MESSAGES`、`LANG` 优先级解析，非 `zh` 使用英语。
- 安装器及独立导出白名单由 13 项增为 15 项，新增 `I18n.js` 和 `i18n.py`。桌面菜单默认 Agent Entry，包含 `zh_CN` / `zh_TW` 名称与说明。
- 四份包配方和公开插件的静态检查通过。根目录测试 **80 项**、插件测试 **37 项**，合计 **117 项通过**；其中 12 项新增语言测试覆盖 locale 优先级、偏好保存、错误翻译和自定义数据保留。
- 使用与 0.2.0 相同固定提交和哈希的官方校验器，对源码与独立导出目录再次校验通过。导出的 **15 个文件**逐字节匹配来源，文件集合严格等于白名单。
- **PySide6-Essentials 6.7.3 / offscreen / software** 真实渲染通过中英文主界面、注册弹窗及英文类型菜单、800px 窄屏、滚动后 Wake 入口；测试实际点击语言按钮并检查动作参数，确认切换语言保留未保存项目输入与 Web 类型，处理中状态同步翻译。测试隔离真实用户配置，不启动应用。
- 当前检查没有加载 Quickshell 宿主；`BarWidget.qml` / `Dashboard.qml` IPC、Linux 安装和真实账户演示仍需在目标 Omarchy 中验收。此前 0.2.0 记录保留如下。
- 实机待验收：双语标签与消息、面板切换后重开及重登保存、`language en` 的英文演示、`language auto` 的 locale 回退。Linux 安装、Quickshell/Hyprland 宿主和两种架构运行继续标记待验证。

## 2026-10-17 · 0.2.0 迁移记录

### 已完成

- 四份 Arch 包配方仍通过 `tools/check-package` 静态检查；未将源码目录的变化混作 Linux 构建证据。
- `tools/check-plugin` 检查 manifest、公开目录索引、入口路径、部署白名单、Python 语法和许可证通过。
- 仓库工具测试 **63 项**，插件测试 **24 项**，共 **87 项通过**。插件测试隔离配置并模拟外部调用，不读取凭据、下载软件、登录或启动 Agent。
- 使用官方 `omarchy-plugin-validate` 脚本校验源码目录与独立导出目录。固定上游提交 `cce8b1c971df64a7610b818ff8819e4bea04584a`，脚本 SHA-256 为 `b6f6aba33a329a5ccd339050fbb2ce82272b791dd1f0d6a28c1837caa035b8c4`。
- 独立导出逐字核对 **13 个白名单文件**，根目录包含 manifest、运行源码、安装器、许可证及文档；没有转换器、开发测试、缓存或运行配置。
- 用临时虚拟环境中的 **PySide6-Essentials 6.7.3**，在 offscreen/software 后端真实渲染 `DashboardContent.qml`。终端动作、Qoder 安装说明、注册对话框、Esc、窗口缩放，以及窄窗口滚动后点击 QoderWake 说明均通过。测试不启动真实应用。
- GitHub Actions YAML 可解析，本地 Markdown 文件链接检查通过。新增 CI 会运行插件单测、官方 manifest 校验和通用 QtQuick 渲染；迁移已推送到 GitHub。首轮 Linux CI 的 manifest 与插件单测通过；Qt 导入因镜像缺少 `libEGL.so.1` 失败，已在工作流补充 `libegl1` / `libopengl0`，后续以修复后的运行结果为准。

### 兼容性处理

- Desktop、IDE 与 CLI 分开检测，CLI 不再把桌面版 `qoder` 当作命令入口。
- 删除旧 DEB 转换器和在线安装流程，只打开对应包或官方说明；软件与插件有独立生命周期。
- Omarchy 插件、钩子遵循官方扫描的 `~/.config/omarchy/`；Agent 自身配置及备份遵循 `XDG_CONFIG_HOME`。
- 保留历史 npm Codex 路径作为命令发现的末尾回退，已安装的旧命令仍可识别；没有恢复 npm 安装功能。
- 从已部署源码执行 `--replace` 会在移动文件前拒绝；升级从新源码或独立导出目录运行。旧目录及插件拥有的入口会先备份，用户配置与应用保留。

### 待目标系统验收

Quickshell 宿主中的 `BarWidget.qml` / `Dashboard.qml`、Hyprland、会话 IPC、登录钩子及实际应用启动没有运行。x86_64 / aarch64 需分别验证插件发现、启用、面板切换、项目目录、自定义入口、应用登录、升级与卸载。纯 QML/Python 的架构无关源码不等于两架构运行通过。

官方校验器与通用 QtQuick 界面检查各有范围，不能替代目标桌面验证。后续将真实机器、Omarchy 版本、架构、提交及每项结果追加到这里。
