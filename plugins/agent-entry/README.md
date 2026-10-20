# Agent Entry · Omarchy 插件

<!-- Modified 2026-10-19: bilingual UI, persisted language choice and English demonstration setup. -->

通过 Quickshell 顶栏按钮展开 Agent 启动面板。界面使用 QML，操作由 Python 标准库脚本处理。当前版本 **0.4.0**，保留插件 ID `anolisa.agent-entry` 和原有配置位置，方便原型用户迁移。

源码来自公开 ANOLISA 实验，采用 **Apache-2.0**；详见 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和固定版本的[来源与修改记录](ORIGIN.md)。本目录不适用仓库原创代码的 0BSD 许可。


AW 入口调用已安装的 `/usr/bin/aw-launch`，进入 Tokenless/可选 sec-core 的首次配置或日常 `aw run`。从仓库根目录执行 `./omarchy-tools aw` 可一次完成软件安装、面板部署与首次启动；后续点击 AW 卡片。Qoder CLI 卡片仍是原生直连入口。仅检测到入口不代表 Provider 已生效。

## 功能与打包边界

- 顶栏切换面板；可选登录后自动显示。
- 英语 / 中文界面；随系统语言或手动选择，设置跨重启保留。
- 在指定项目目录打开 Shell Terminal、cosh-ng、Qoder CLI、Codex CLI 或 QoderWake。
- 分别检测和启动 Qoder Desktop 与 Qoder IDE；Qoder CLI 只探测 `qodercli`，避免把 GUI 的 `qoder` 命令认作 CLI。
- 添加自定义终端命令、GUI 命令或 Web URL；命令存为参数数组。
- 缺少应用时，「安装说明」按钮在浏览器中打开对应配方说明或官方指南。面板不下载、构建或安装应用。

| 入口 | 默认检测方式 | 安装说明 |
| --- | --- | --- |
| Qoder Desktop | `qoder.desktop` / `qoder-desktop.desktop`，或 `qoder-desktop` / `Qoder` | [qoder-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-bin/README.md) |
| Qoder IDE | `qoder-ide.desktop` / `qoderide.desktop`，或 `qoder-ide` / `QoderIDE` | [qoder-ide-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-ide-bin/README.md) |
| Qoder CLI | `qodercli` | [qodercli-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qodercli-bin/README.md) |
| QoderWake | `qoderwake` | [qoderwake-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoderwake-bin/README.md) |
| Codex CLI | `codex` | [官方仓库](https://github.com/openai/codex) |
| cosh-ng | `cosh-ng` / `cosh` | [ANOLISA](https://github.com/casparant/ANOLISA) |

仓库里的 Qoder 配方仍是候选，尚未发布到 AUR 或 Omarchy 包源；安装与验证状态以对应包说明为准。应用文件由 pacman 管理，插件只负责启动和引导。旧原型自带的 DEB 转换器与厂商脚本下载器已移除。旧版安装到用户 npm 目录的 Codex 仍可被发现；该路径只作兼容回退，优先使用当前 PATH 中的版本，不再执行安装或更新。

面板不保存或读取登录凭据。检测到命令只说明存在启动入口，不代表登录成功或程序可运行。登录在各应用原生界面完成。收起面板不会结束已打开的终端或应用。

## 在 Omarchy 上部署

需要提供 Quickshell 插件接口的 Omarchy 桌面会话、`omarchy`、`omarchy-shell`、**Python 3.9+**、`xdg-open`，以及 foot / kitty / alacritty / xterm 中的一种终端。`gtk-launch` 可用于桌面文件启动；没有它时尝试表中的命令。软件本体需单独安装。

原型针对 Omarchy 4.0.1 开发。本次迁移完成源码、隔离测试和通用 QtQuick 离屏界面测试，尚未完成 Linux/Hyprland/Omarchy 实机验收。

在仓库中执行，使用当前图形会话的普通用户：

```bash
./omarchy-tools panel
# 已安装旧版时升级；需要登录后显示再加 --autostart
./omarchy-tools panel --replace
```

如果使用独立导出目录，在其根目录直接执行 `python3 install.py`，无需根目录工具；升级使用 `python3 install.py --replace`，登录后显示使用 `--autostart`。

安装器先执行官方 `omarchy plugin validate`，再复制本目录的明确文件清单、注册菜单入口并启用插件。部署文件自包含，不依赖源仓库上级目录，也不改变软件源或系统软件包。

| 内容 | 默认位置 |
| --- | --- |
| 插件 | `~/.config/omarchy/plugins/anolisa.agent-entry/` |
| 命令入口 | `~/.local/bin/anolisa-agent-entry` |
| 应用菜单入口 | `~/.local/share/applications/anolisa-agent-entry.desktop` |
| 可选登录钩子 | `~/.config/omarchy/hooks/post-boot.d/anolisa-agent-entry.sh` |
| 项目与自定义入口 | `~/.config/anolisa/agent-entry.json` |
| 升级、卸载备份 | `~/.config/anolisa/plugin-backups/` |

设置了 `XDG_CONFIG_HOME` 时，Agent 自身的 `anolisa/agent-entry.json` 与 `anolisa/plugin-backups/` 采用该位置。Omarchy 的插件与登录钩子始终位于 `~/.config/omarchy/`，与官方发现机制一致；不修改已有 Hyprland 配置或其他钩子。

## 界面语言与英文演示

面板右上角「收起 / Close」右侧的语言按钮立即切换界面，并保存选择：中文界面显示 **English**，英文界面显示 **中文**。默认 `language: "auto"`，依次使用 `LC_ALL`、`LC_MESSAGES`、`LANG` 的第一个非空值；`zh` 系列 locale 使用中文，其余使用英语。可保存的值是 `auto`、`en`、`zh`；已有配置无需迁移，未设置时按 `auto` 处理。应用品牌、自定义入口名、命令与路径保持原样。

更新源码后先重新部署；只拉取仓库不会改变已安装的插件。给英语观众演示前执行：

```bash
./omarchy-tools panel --replace
~/.local/bin/anolisa-agent-entry language en
~/.local/bin/anolisa-agent-entry open
```

此后重新打开面板仍为英语。命令入口也可以切回中文或系统语言：

```bash
~/.local/bin/anolisa-agent-entry language zh
~/.local/bin/anolisa-agent-entry language auto
```

选择保存在上表的 `agent-entry.json` 的 `language` 字段。手动编辑可设 `"language": "en"`；再次打开面板读取。安装后的应用菜单默认名称为 **Agent Entry**，中文系统菜单显示 **Agent 入口**；菜单语言由桌面 locale 决定，独立于面板选择。

## 首次使用与自定义入口

1. 点击顶栏「Agent Entry / Agent 入口」，打开 Shell Terminal，确认项目目录。
2. 未安装的软件先查看「安装说明」，按配方文档审阅并安装。
3. 刷新面板后启动软件，在原生界面完成登录。
4. 如需自定义命令，点击「添加入口」，或编辑配置中的 `commands`。

QoderWake 仅在点击后才尝试 `whoami`，需要时执行原生 `login`，再调用 `start --host 127.0.0.1 --open`。此行为继承自原型，仍待目标系统运行验证；软件包自带的可选 systemd 用户服务与原生命令的管理方式见包说明。

下面的配置片段用于已有命令的显式覆盖；合并到现有配置中，路径改成目标机器上的实际值：

```json
{
  "version": 1,
  "project": "/home/you/Projects",
  "language": "auto",
  "commands": {
    "cosh": ["/opt/anolisa/bin/cosh-ng"],
    "qoder-cli": ["/home/you/.local/bin/my-qoder-cli"]
  },
  "agents": []
}
```

也可以通过命令注册自定义入口：

```bash
~/.local/bin/anolisa-agent-entry register my-tool "我的工具" terminal '["/path/to/tool"]'
~/.local/bin/anolisa-agent-entry register console "本地 Console" web 'http://127.0.0.1:19820'
```

终端工作目录使用项目目录。GUI 如果通过 `gtk-launch` 启动，由应用决定是否恢复项目；项目目录不代表通用 GUI 打开项目协议。插件不是嵌入式终端或任务监控器。

## 升级、卸载与诊断

从新源码或插件导出目录升级。不能在已部署的插件目录内执行 `--replace`，安装器会在移动文件前拒绝，防止把当前复制来源移入备份：

```bash
python3 install.py --replace
# 需要登录后显示时加 --autostart
python3 install.py --replace --autostart
```

原型中遗留的 `qoder/` 转换器随旧插件一起备份，新版本不携带或调用它。插件升级不升级应用；软件、账号、项目配置分别保留。

卸载可从源码目录执行，也可使用已经部署的安装器：

```bash
python3 install.py --uninstall
# 默认部署位置，无需保留源码仓库
python3 ~/.config/omarchy/plugins/anolisa.agent-entry/install.py --uninstall
```

插件、菜单、命令与登录钩子移至备份目录；应用安装和 `agent-entry.json` 不删除。仅关闭登录显示时，移走该插件的 `post-boot.d` 钩子即可。

```bash
~/.local/bin/anolisa-agent-entry status
~/.local/bin/anolisa-agent-entry open
omarchy-shell shell listPlugins
omarchy-shell shell rescanPlugins
omarchy plugin enable anolisa.agent-entry
```

## 测试与验收

测试文件只保留在本仓库源码中，不随运行文件导出。在源码目录执行：

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

0.2.0 于 2026-10-17 在 macOS 的 Python 3.9.6 上通过 24 项隔离测试，5 个 Python 文件均通过源码编译检查。0.3.0 新增语言选择、locale 回退、双语界面及菜单资源检查；本轮结果见[验证记录](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/plugins-validation.md)。自动化测试覆盖命令隔离、参数数组、配置、安装说明链接、Wake 启动参数、旧 Codex 发现回退、自定义 XDG 配置与官方插件路径、升级预检、备份升级和可恢复卸载。它们不代替软件本体运行。可选真实 QtQuick 排版测试需要开发环境安装 PySide6，部署不依赖它：

```bash
python3 -m venv /tmp/agent-entry-qt
/tmp/agent-entry-qt/bin/python -m pip install -r tests/requirements-qt.txt
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software /tmp/agent-entry-qt/bin/python tests/render_qml.py /tmp/agent-entry-preview.png
```

0.2.0 已使用 PySide6-Essentials 6.7.3、offscreen/software 后端完成真实 QtQuick 渲染及交互测试：终端与安装说明动作、注册弹窗、Esc、窄窗口滚动与 QoderWake 按钮均通过。官方 Omarchy manifest 验证器（提交 `cce8b1c971df64a7610b818ff8819e4bea04584a`）检查通过；这些结果不代表 Quickshell 宿主或目标 Linux 会话已运行。

**待实机验收**：两种 CPU 架构分别安装插件 → 英语/中文切换、持久化及系统语言回退 → 顶栏展开/收起 → 启动终端与已安装应用 → 添加自定义入口 → 打开安装说明 → 原生登录 → 注销重登确认可选钩子 → 升级及卸载。`x86_64` / `aarch64` 表示源码使用与 CPU 架构无关的 QML/Python，不代表这两种架构已经运行通过。
