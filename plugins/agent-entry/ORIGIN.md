# 来源与修改记录

本目录移自公开的 ANOLISA Agent Entry 原型：

- 仓库：[casparant/ANOLISA](https://github.com/casparant/ANOLISA)
- 分支：`feature/desktop/omarchy-agent-entry`
- 提交：[`a34f94ba0050d15b6404f349d86de2ebf6c5b880`](https://github.com/casparant/ANOLISA/commit/a34f94ba0050d15b6404f349d86de2ebf6c5b880)
- 路径：`experiments/omarchy-agent-entry/`
- 上游许可：Apache License, Version 2.0；完整文本保留于 [LICENSE](LICENSE)。
- 相关上游署名保留于 [NOTICE](NOTICE)：ANOLISA，Copyright 2026 Alibaba Cloud。

上游根 NOTICE 还列有其他 ANOLISA 组件及其依赖，这些代码未被迁入。本目录只保留与本次移入源码相关的项目声明；没有打包任何第三方应用二进制。

## 2026-10-20 · 0.5.1

- 恢复「安装」动作：目录中存在的软件可以在终端里由仓库 `omarchy-tools` 构建本地配方安装。0.2.0 移除 `install` / `install-run` 的理由是当时只剩厂商 DEB 转换器和在线安装脚本；`omarchy-tools` 已在 2026-10-19 提供了不执行厂商脚本、只用固定配方的路径，因此那条限制不再成立，本条为有意撤销。
- 插件不自行装软件：`install` 只在用户终端中发起任务，`install-run` 才在该终端里调用 `omarchy-tools install <软件名>`，命令与 `sudo` 提示都由用户在窗口内亲自确认，助手进程不代答提权。
- `omarchy-tools` 按命令名发现（PATH，或 `OMARCHY_TOOLS` 指定脚本），插件源码不含任何仓库绝对路径；发现不到、或该入口不在目录软件中时，卡片退回「安装说明」，状态与旧版一致。
- 安装器把上级目录的 `omarchy-tools` 链接到 `~/.local/bin/omarchy-tools`；该位置已有文件或指向别处时保留不动，卸载只回收自己创建的这一条。
- 与 0.5.0 的只读工作台并存：工作台仍不写状态、不启后台，安装动作走独立终端；`aw` 入口同时具备工作台展示与目录安装映射。
- 根策略同步修改：AGENTS.md 中"插件只启动应用并链接说明"一条现明确允许上述委托方式。

## 2026-10-20 · 0.5.0

- 将 AW 启动卡片扩展为只读工作台，分开展示服务、历史压缩统计、策略与后台健康及最近步骤。
- 复用公开 `aw-panel/v1alpha1` 与 `aw-sec-core-health/v1alpha1`，保留 `unknown` / `unverified` 的证据边界；不改变 AW、安全策略或 Qoder 原生授权。
- 新增有时限与输出上限的查询、错误状态及双语界面回归；更新部署白名单。
- 回归 fixture 来自公开 [ANOLISA 提交 696e1aa0](https://github.com/agentic-os-org/ANOLISA/tree/696e1aa0c02e9c6a6817bc68c2101f7034d52c59/src/aw/crates/aw-provider/examples/views)，保留上游 Apache-2.0 署名。测试数据不随插件部署。

## 2026-10-20 · 0.4.1

- 承接 0.4.0（AW 预编译包启动入口）；本轮只改 GUI 聚焦与测试隔离。
- GUI 入口在应用已经运行时改为请合成器把现有窗口切到前台，不再重复发起进程。此前重复启动会撞上单实例锁后立刻退出，窗口不动，用户看到「点了没反应」。0.4.0 在 `launch` 返回 0 时收起面板，与本修改叠加后：聚焦既有窗口 → 面板收起 → 原生窗口到前台。
- 窗口匹配从要启动的桌面文件读取 `StartupWMClass`，并锚定为 `^…$` 正则：不硬编码类名，上游改类名后自动跟随；不锚定则 `qoder` 会匹配到 `qoder-ide` 的窗口。
- 没有 `omarchy`、没有桌面文件或聚焦失败时，行为与本修改前完全一致（照常启动），不改变非 Hyprland 环境的可用性。
- 桌面文件查找与系统目录扫描收敛到 `desktop_dirs()`。原 `test_desktop_and_ide_are_independent` 只隔离了 `Path.home()`，在装有 `qoder.desktop` 的 Linux 主机上必然失败；本轮在 Omarchy 实机合并 0.4.0 后以 42 项插件测试、119 项仓库测试通过。

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

## 0.6.0 · Control plane PoC

- Add a quiet compact panel and a detailed component view using existing read-only queries.
- Project configured hook order and error actions without claiming native adoption.
- Discover the actual cosh entry; reserve its herdr run view for later integration.
- Remove Qoder launch from the AW status card; preserve native launch and security helpers.
