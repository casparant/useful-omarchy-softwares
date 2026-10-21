# Agent Entry · Omarchy 插件

## 会话工作台 PoC（0.7）

顶栏 AW 提供紧凑摘要，详情显示真实会话、固定策略版本与运行代次。
cosh 是真正的 AI Shell；在其中运行 `aw run --agent qoder`，由 herdr 托管终端并经 AW 启动 Qoder。
关闭窗口后可返回同一活进程与对话；Panel 的“返回”不会新建 Agent。
新建用 `aw run --agent qoder`，继续已有会话用“返回”。适配仅存在于插件的 cosh Bash 后台，
保留显式 `--config`、native 选项和 `--` 后参数；普通终端保持原生 AW 行为。
安装后首次执行 `aw-session setup` 配置 herdr 官方 Qoder 身份 Hook。
“Hook 已绑定”来自存活进程、原生 Hook/binding 和在线 AW 实例的交叉核验；
不等于 API adoption 已验证或每次调用均获准。VM 重启续接和热更新未启用。
要求已安装 cosh、herdr、AW、Qoder，详见
[使用、证据与边界](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/agent-control-plane-poc.md)。

<!-- Modified 2026-10-19: bilingual UI, persisted language choice and English demonstration setup. -->

通过 Quickshell 顶栏按钮展开 Agent 启动面板。界面使用 QML，操作由 Python 标准库脚本处理。当前版本 **0.7.0**，保留插件 ID `anolisa.agent-entry` 和原有配置位置，方便原型用户迁移。

源码来自公开 ANOLISA 实验，采用 **Apache-2.0**；详见 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和固定版本的[来源与修改记录](ORIGIN.md)。本目录不适用仓库原创代码的 0BSD 许可。


现有 `/usr/bin/aw-launch` 继续提供 Tokenless/可选 sec-core 的首次配置或日常 `aw run`。从仓库根目录执行 `./omarchy-tools aw` 可一次完成软件安装、面板部署与首次启动；日常可从 cosh 终端执行 `aw run --agent qoder`。AW 状态区只提供查询与说明，Qoder CLI 卡片仍是原生直连入口。仅检测到入口不代表 Provider 已生效。

## AW 工作台与首次登录

工作台在面板可见时每 5 秒读取一次已安装 AW 的状态，收起后停止轮询。
使用现有 `aw inspect --json` 和 sec-core 只读健康接口，不启动后台、不扫描项目、
不执行压缩或修改策略。查询失败会清除旧数字并明确显示无法查询。

- **AW**：展示后台在线、未运行、未配置或无法查询；在线不等于当前 Agent 已接入。
- **Tokenless**：展示存储中最近最多 200 条记录的压缩前后估算 token 数、减少数量和比例。
  这是组件历史统计，不是当前会话计费，也不代表全部模型上下文；无数据时显示「—」。
- **sec-core**：分别展示策略是否配置/启用与后台是否认证可达；健康不代表准入或检查通过。
- **最近活动**：受管会话详情展示其独立 AW 实例的最近 3 条步骤；旧软件目录展示默认实例的前 5 条。Tokenless 请求改写重试、
  安全策略阻断、异常阻断、完成观察与压缩完成分别标注；不显示工具命令、输出或凭据。
  「查看详情」仅展开同一份筛选后的展示数据。

工作台识别预编译包和 `$XDG_CONFIG_HOME/aw/preview.yaml`（默认 `~/.config/aw/preview.yaml`）。
显式覆盖 AW 启动命令时仍能启动，但不推断其状态。Qoder CLI 卡片为直接启动入口；
需要托管和 AW Hook 时在 cosh 终端使用 `aw run --agent qoder`，首次配置、目录信任与工具权限继续由终端和 Qoder 原生界面确认。
Tokenless 请求重试后的命令仍要经过安全检查与原生权限；不建议为演示全局放行 `env`。

演示电脑无需访问内网仓库。安装需要公开 GitHub、Arch/Omarchy 软件源和 Qoder 公开下载服务；
登录与模型调用需要联网访问 Qoder 服务。在 [Qoder 账户集成页](https://qoder.com/account/integrations)
创建 **Personal Access Token (PAT)**，与模型供应商的 `sk-` API Key 不同。
首次 `./omarchy-tools aw` 配置后进入 Qoder，确认项目目录信任，选择 **Sign in to continue**（已进入会话时输入 `/login`），
选择 **Use Qoder Personal Access Token** 并粘贴 PAT；浏览器登录也保留。
注意 `qodercli login` 子命令只进入浏览器流程，PAT 入口是交互界面的 `/login`。
不要把 PAT 填进 AW YAML、Panel 配置、shell 命令或截图；本插件不保存或读取凭据。
公开认证说明见 [Qoder CLI authentication](https://docs.qoder.com/cli/authentication)。

## 功能与打包边界

- 顶栏切换面板；可选登录后自动显示。
- 英语 / 中文界面；随系统语言或手动选择，设置跨重启保留。
- 在指定项目目录打开 Shell Terminal、cosh-ng、Qoder CLI、Codex CLI 或 QoderWake。
- 分别检测和启动 Qoder Desktop 与 Qoder IDE；Qoder CLI 只探测 `qodercli`，避免把 GUI 的 `qoder` 命令认作 CLI。
- GUI 应用已在运行时，「打开」请合成器把现有窗口切到前台，不再重复发起进程撞单实例锁导致毫无反应。
- 添加自定义终端命令、GUI 命令或 Web URL；命令存为参数数组。
- 缺少应用时分两种动作：目录里有对应软件、且能发现 `omarchy-tools` 时，「安装」在你的终端里调用它构建本地配方（执行的命令与 `sudo` 提示都出现在那个窗口，面板不代答、不静默提权）；否则「安装说明」在浏览器中打开对应配方说明或官方指南。面板不下载厂商脚本、不做包格式转换，也不会绕过目录自己装东西。

| 入口 | 默认检测方式 | 安装说明 |
| --- | --- | --- |
| Qoder Desktop | `qoder.desktop` / `qoder-desktop.desktop`，或 `qoder-desktop` / `Qoder` | [qoder-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-bin/README.md) |
| Qoder IDE | `qoder-ide.desktop` / `qoderide.desktop`，或 `qoder-ide` / `QoderIDE` | [qoder-ide-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-ide-bin/README.md) |
| Qoder CLI | `qodercli` | [qodercli-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qodercli-bin/README.md) |
| QoderWake | `qoderwake` | [qoderwake-bin](https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoderwake-bin/README.md) |
| Codex CLI | `codex` | [官方仓库](https://github.com/openai/codex) |
| cosh-ng | `cosh-ng` / `cosh` | [ANOLISA](https://github.com/casparant/ANOLISA) |

仓库里的 Qoder 配方仍是候选，尚未发布到 AUR 或 Omarchy 包源；安装与验证状态以对应包说明为准。应用文件由 pacman 管理，插件只负责启动、引导和把安装动作交给仓库 `omarchy-tools`，自身不装软件。旧原型自带的 DEB 转换器与厂商脚本下载器已移除。旧版安装到用户 npm 目录的 Codex 仍可被发现；该路径只作兼容回退，优先使用当前 PATH 中的版本，不再执行安装或更新。

面板不保存或读取登录凭据。检测到命令只说明存在启动入口，不代表登录成功或程序可运行。登录在各应用原生界面完成。收起面板不会结束已打开的终端或应用。

## 在 Omarchy 上部署

需要提供 Quickshell 插件接口的 Omarchy 桌面会话、`omarchy`、`omarchy-shell`、**Python 3.9+**、`xdg-open`，以及 foot / kitty / alacritty / xterm 中的一种终端。`gtk-launch` 可用于桌面文件启动；没有它时尝试表中的命令。软件本体需单独安装。「安装」按钮额外要求能发现 `omarchy-tools`（命令名在 PATH 上，或由 `OMARCHY_TOOLS` 指向该脚本）；发现不到时卡片自动退回「安装说明」，其余功能不受影响。

原型针对 Omarchy 4.0.1 开发。0.5.0 在 Omarchy ARM64 VM 验证，范围见下方测试与验收；x86_64 桌面仍需现场验收。

在仓库中执行，使用当前图形会话的普通用户：

```bash
./omarchy-tools panel
# 已安装旧版时升级；需要登录后显示再加 --autostart
./omarchy-tools panel --replace
```

如果使用独立导出目录，在其根目录直接执行 `python3 install.py`，无需根目录工具；升级使用 `python3 install.py --replace`，登录后显示使用 `--autostart`。

安装器先执行官方 `omarchy plugin validate`，再复制本目录的明确文件清单、注册菜单入口并启用插件。运行中的插件自包含，不读取源仓库位置；安装器另外尝试把上一级目录的 `omarchy-tools` 链接到 `~/.local/bin/omarchy-tools` 供「安装」按钮发现，该位置已有文件或已指向别处时一律保留不动，卸载只回收自己创建的这一条链接。两种方式都不改变软件源或系统软件包。

| 内容 | 默认位置 |
| --- | --- |
| 插件 | `~/.config/omarchy/plugins/anolisa.agent-entry/` |
| 命令入口 | `~/.local/bin/anolisa-agent-entry` |
| 应用菜单入口 | `~/.local/share/applications/anolisa-agent-entry.desktop` |
| 安装入口发现（可选，仅由安装器创建） | `~/.local/bin/omarchy-tools` |
| 可选登录钩子 | `~/.config/omarchy/hooks/post-boot.d/anolisa-agent-entry.sh` |
| 项目与自定义入口 | `~/.config/anolisa/agent-entry.json` |
| 升级、卸载备份 | `~/.config/anolisa/plugin-backups/` |

设置了 `XDG_CONFIG_HOME` 时，Agent 自身的 `anolisa/agent-entry.json` 与 `anolisa/plugin-backups/` 采用该位置。Omarchy 的插件与登录钩子始终位于 `~/.config/omarchy/`，与官方发现机制一致；不修改已有 Hyprland 配置或其他钩子。

## 界面语言与英文演示

面板右上角「收起 / Close」右侧的语言按钮立即切换界面，并保存选择：中文界面显示 **English**，英文界面显示 **中文**。默认 `language: "auto"`，依次使用 `LC_ALL`、`LC_MESSAGES`、`LANG` 的第一个非空值；`zh` 系列 locale 使用中文，其余使用英语。可保存的值是 `auto`、`en`、`zh`；已有配置无需迁移，未设置时按 `auto` 处理。应用品牌、自定义入口名、命令与路径保持原样。

更新源码后先重新部署；只拉取仓库不会改变已安装的插件。若升级后仍是旧布局，当前 Quickshell 可能保留旧 QML 缓存；保存工作后注销并重新登录桌面。安装器不会自动重启桌面。给英语观众演示前执行：

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

安装动作与终端类入口同构成对：`install` 只负责在你的终端里发起任务，`install-run` 才在那个终端中调用 `omarchy-tools install <软件名>` 并流式显示构建输出。目录里没有对应软件、或发现不到 `omarchy-tools` 时，两者都直接报错，不会退化成静默安装或改用别的来源。

```bash
~/.local/bin/anolisa-agent-entry install qoder-ide      # 打开终端开始安装
~/.local/bin/anolisa-agent-entry install-run qoder-ide  # 终端内的实际构建步骤
```

终端工作目录使用项目目录。GUI 如果通过 `gtk-launch` 启动，由应用决定是否恢复项目；项目目录不代表通用 GUI 打开项目协议。插件不嵌入终端，安装与终端会话都在独立窗口中运行；AW 工作台只显示只读摘要。

GUI 聚焦依赖 `omarchy hyprland focus app`（Hyprland 专用），匹配类名取自桌面文件的 `StartupWMClass` 并按 `^…$` 锚定。找不到该命令、没有桌面文件或窗口不存在时，退回原本的启动行为。注意 Omarchy 4 的 Hyprland 0.56 使用 Lua 配置，传统 `hyprctl dispatch <子命令> <参数>` 会被当作 Lua 源码而失败，正确形式是 `hyprctl dispatch 'hl.dsp.focus({ window = "address:…" })'`；这也是任何外部脚本在本机上聚焦窗口的通用坑。

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

0.2.0 于 2026-10-17 在 macOS 的 Python 3.9.6 上通过 24 项隔离测试，5 个 Python 文件均通过源码编译检查。0.3.0 新增语言选择、locale 回退、双语界面及菜单资源检查；本轮结果见[验证记录](https://github.com/casparant/useful-omarchy-softwares/blob/main/docs/plugins-validation.md)。0.4.1 在 Omarchy 4.0.5 `x86_64`（Python 3.14.8）实机、合并 0.4.0 之后通过 42 项插件测试与 119 项仓库测试，并在同机确认聚焦链路本身可用：`omarchy hyprland focus app '^qoder$'` 退出码 0，`hyprctl activewindow` 复核为 `class=qoder`，未运行的应用退出码 1。这是助手脚本层的结果，不代表 Quickshell 面板点击链路已经验收。自动化测试覆盖命令隔离、参数数组、配置、安装说明链接、Wake 启动参数、旧 Codex 发现回退、自定义 XDG 配置与官方插件路径、升级预检、备份升级和可恢复卸载。它们不代替软件本体运行。可选真实 QtQuick 排版测试需要开发环境安装 PySide6，部署不依赖它：

```bash
python3 -m venv /tmp/agent-entry-qt
/tmp/agent-entry-qt/bin/python -m pip install -r tests/requirements-qt.txt
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software /tmp/agent-entry-qt/bin/python tests/render_qml.py /tmp/agent-entry-preview.png
```

0.2.0 已使用 PySide6-Essentials 6.7.3、offscreen/software 后端完成真实 QtQuick 渲染及交互测试：终端与安装说明动作、注册弹窗、Esc、窄窗口滚动与 QoderWake 按钮均通过。官方 Omarchy manifest 验证器（提交 `cce8b1c971df64a7610b818ff8819e4bea04584a`）检查通过；这些结果不代表 Quickshell 宿主或目标 Linux 会话已运行。

**待实机验收**：两种 CPU 架构分别安装插件 → 英语/中文切换、持久化及系统语言回退 → 顶栏展开/收起 → 启动终端与已安装应用 → 添加自定义入口 → 打开安装说明 → 原生登录 → 注销重登确认可选钩子 → 升级及卸载。`x86_64` / `aarch64` 表示源码使用与 CPU 架构无关的 QML/Python，不代表这两种架构已经运行通过。
