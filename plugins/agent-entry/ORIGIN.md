# 来源与修改记录

本目录移自公开的 ANOLISA Agent Entry 原型：

- 仓库：[casparant/ANOLISA](https://github.com/casparant/ANOLISA)
- 分支：`feature/desktop/omarchy-agent-entry`
- 提交：[`a34f94ba0050d15b6404f349d86de2ebf6c5b880`](https://github.com/casparant/ANOLISA/commit/a34f94ba0050d15b6404f349d86de2ebf6c5b880)
- 路径：`experiments/omarchy-agent-entry/`
- 上游许可：Apache License, Version 2.0；完整文本保留于 [LICENSE](LICENSE)。
- 相关上游署名保留于 [NOTICE](NOTICE)：ANOLISA，Copyright 2026 Alibaba Cloud。

上游根 NOTICE 还列有其他 ANOLISA 组件及其依赖，这些代码未被迁入。本目录只保留与本次移入源码相关的项目声明；没有打包任何第三方应用二进制。

## 2026-10-19 · 0.3.0

- 将顶栏、面板、对话框与操作反馈改为英语 / 中文，新增自包含 `I18n.js` 与 `i18n.py`；应用品牌、用户名称、路径和命令不翻译。
- 增加 `language` 配置与 `language auto|en|zh` 命令；默认按 `LC_ALL`、`LC_MESSAGES`、`LANG` 解析系统语言，非中文 locale 使用英语，面板内切换后保存选择。
- 显示名称统一为 Agent Entry，保留稳定插件 ID `anolisa.agent-entry`、原有配置、Apache-2.0 许可证与署名；桌面菜单增加简体及繁体中文本地化。
- 部署和独立导出白名单同步包含两份语言资源；更新测试、升级说明及英文演示命令。

本轮验证范围与尚待完成的目标机器验收见[验证记录](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/plugins-validation.md)。

## 2026-10-17 · 0.2.0

- 保留插件 ID、配置结构、顶栏与面板接口、原生应用启动和自定义入口。
- 将 Qoder Desktop、IDE、CLI 分开探测；移除 CLI 对裸 `qoder` 的探测。
- 移除 `qoder/` DEB 转换器与其测试、在线安装脚本执行和用户 npm 安装操作；保留旧 npm 目录作为 Codex 命令发现的末尾回退。
- 缺少软件时，在浏览器打开具体配方 README 或官方安装指南；移除 `install` 与 `install-run` 命令。
- 本地安装器仅复制明确清单中的自包含插件与许可文件，同时保留安装器以支持离线卸载；Agent 自身配置和备份遵循 `XDG_CONFIG_HOME`，Omarchy 插件与钩子仍使用官方扫描的 `~/.config/omarchy/`。
- 升级时备份旧插件（包括原型遗留转换器），保留应用、账户与用户配置；就地替换已部署源码会在移动文件前拒绝。
- 更新文档与功能测试；版本及说明字段在 `manifest.json` 中更新。

已修改的 Python/QML 文件和说明带有迁移修改标记；`manifest.json` 的版本由 0.1.0 改为 0.2.0，description 改为包说明入口。其余未修改的 QML 文件保持上游原样。

已进行源码、隔离测试、官方 manifest 校验与通用 QtQuick 离屏渲染/交互测试。未声明 Linux、Quickshell 宿主、Wayland、登录流程或任一架构实机测试通过。

AW 集成增加独立的预编译包启动入口；成功请求启动后收起面板，让原生终端获得焦点。保留原生 Qoder 入口、配置和 Apache-2.0 许可。
