# Useful Omarchy Softwares

为 Arch Linux / Omarchy 维护实用软件的标准包配方、Quickshell 桌面插件、适配记录与测试流程。先把包做成独立可审阅的 `PKGBUILD`，再参与 AUR 维护或向 Omarchy 官方包仓库贡献。

当前以 QoderWake 为首包，扩展到 Qoder CLI、桌面版和 IDE；钉钉复用已有 Omarchy 配方。这里保存配方和自己编写的辅助代码，第三方软件在构建时从官方地址下载。

## Quickstart

在 **Omarchy 图形会话的普通用户终端**执行，需要 Python 3.9+ 和 sudo。首次获取代码：

```bash
git clone https://github.com/casparant/useful-omarchy-softwares.git
cd useful-omarchy-softwares
```

**一条命令装面板：**

```bash
./omarchy-tools panel
```

**一条命令装软件：**

```bash
./omarchy-tools install qoderwake
```

面板会部署并打开；软件安装完成后，按对应包说明首次登录与启动。脚本会准备所需系统依赖，并保留 pacman 的交互确认；整个脚本用普通用户运行，系统包操作才调用 sudo。安装面板需要带 Quickshell 插件接口的 Omarchy 和 `omarchy-shell`，不支持该接口的旧版 Omarchy 需先升级。

更多操作都走同一个入口：

```bash
./omarchy-tools list                             # 查看软件、架构和安装来源
./omarchy-tools install qoderwake qodercli         # 双架构软件，可一次选择多个
./omarchy-tools install qoder qoder-ide            # 桌面版和 IDE，目前仅 x86_64
./omarchy-tools install dingtalk                   # 使用已配置的 Omarchy 软件源
./omarchy-tools panel --autostart                 # 首次安装，并在登录后显示面板
./omarchy-tools panel --replace                   # 更新面板，旧文件先备份
./omarchy-tools panel --uninstall                 # 卸载面板，保留配置与备份
./omarchy-tools remove qoderwake                  # pacman 卸载软件，保留用户数据
./omarchy-tools --help
```

软件名也可用完整包名，例如 `qoderwake-bin`、`qodercli-bin`、`dingtalk-bin`。所有选择会在安装前检查；ARM 上选择仅支持 x86_64 的软件会提前报错。钉钉若不在当前已配置的软件源中，会给出[现有渠道说明](docs/software/dingtalk.md)。

拉取仓库更新后，重新部署面板或更新需要的软件：

```bash
git pull --ff-only
./omarchy-tools panel --replace
./omarchy-tools update qoderwake qodercli
```

`update` 与 `install` 使用相同流程：本地 Qoder 配方以当前 checkout 固定的版本校验来源、干净重建并通过 pacman 安装；钉钉使用 Omarchy 当前软件源版本。实际安装版本以当前配方为准，旧 checkout 可能导致重装或降级，安装前留意 pacman 确认信息。批量安装中途失败会停止，先前已完成的安装会保留，可在处理错误后只重试未完成的软件。面板更新不更新应用。卸载 Wake 前先按[包说明](pkgbuilds/qoderwake-bin/README.md)停止已运行的 daemon 或用户服务。

本地配方与面板仍处于候选阶段；快捷入口的自动化测试不代表已完成 Omarchy 实机验收，具体验证状态见下方目录与各组件说明。脚本按自身路径定位仓库，也可以从其他目录通过绝对路径调用。

## 软件目录

| 软件 | 本地配方 | 架构 | 进度 |
| --- | --- | --- | --- |
| QoderWake 1.1.12 | [qoderwake-bin](pkgbuilds/qoderwake-bin/README.md) | x86_64 / aarch64 | 已验证来源、ELF 和暂存布局；待 Linux 构建与运行 |
| Qoder CLI 1.1.73 | [qodercli-bin](pkgbuilds/qodercli-bin/README.md) | x86_64 / aarch64 | 本地候选；参与现有 AUR 包维护 |
| Qoder Desktop 0.4.8 | [qoder-bin](pkgbuilds/qoder-bin/README.md) | x86_64 | 本地候选；待 Linux/Wayland 验证 |
| Qoder IDE 1.33.0 | [qoder-ide-bin](pkgbuilds/qoder-ide-bin/README.md) | x86_64 | 本地候选；待 Linux/Wayland 验证 |
| 钉钉 | [安装与调研](docs/software/dingtalk.md) | 上游配方声明双架构 | Omarchy 已有 dingtalk-bin，不重复打包 |

完整来源、维护归属和验证状态见 [catalog.json](catalog.json)。`aarch64` 指 Linux ARM64；不会将 x86 软件改标为 ARM。GUI 两包目前没有确认官方 Linux ARM 产物。

## 桌面插件

[plugins/](plugins/README.md)独立维护 Quickshell 插件。[Agent Entry](plugins/agent-entry/README.md)已从 ANOLISA 公开实验迁入，保留原 ID 和 Apache-2.0 许可，提供顶栏入口、应用/终端启动及安装说明。部署、检查和独立导出流程见插件目录；目标 Omarchy 会话仍待实机验收。

## 在 Arch Linux 上构建首包

先审阅 [QoderWake 配方](pkgbuilds/qoderwake-bin/PKGBUILD) 和[包说明](pkgbuilds/qoderwake-bin/README.md)，再使用普通用户执行：

```bash
sudo pacman -S --needed base-devel git python
cd pkgbuilds/qoderwake-bin
makepkg --verifysource
makepkg -s
sudo pacman -U ./qoderwake-bin-1.1.12-1-*.pkg.tar.zst
```

安装只放置文件，不会登录或启动 Wake。首次运行、可选用户服务、私有配套 CLI、自更新限制见包说明。系统依赖由 pacman 管理；用户数据保留在软件自己的用户目录。

宿主机不是 Arch 时，可在有 Docker/Podman 的 Linux 环境或 Omarchy 官方构建仓库中构建，见[测试流程](docs/testing.md)和[发布流程](docs/publishing.md)。本轮开发环境是 macOS ARM；没有把本地暂存检查写成 Linux 构建或实际可用性验证。

## 检查与维护

仓库工具使用 Python 3.9+ 标准库：

```bash
tools/check-package
tools/check-plugin
python3 -m unittest discover -s tests -v
tools/check-updates
python3 -m unittest discover -s plugins/agent-entry/tests -p 'test_*.py' -v
```

- `check-package [pkgbase]` 检查语法、元数据、固定来源和本地文件校验；有 makepkg 时额外比对 `.SRCINFO`。`--require-makepkg` 用于要求 Arch 元数据验证的环境。
- `check-updates [pkgbase]` 只读官方发布清单，核对版本、架构、下载地址和哈希，不自动改配方或发布。
- `check-plugin [name]` 验证公开插件和部署文件白名单；`export-plugin <name> <新目录>` 导出根目录带 manifest 的独立插件，不执行发布。
- `export-aur <pkgbase> <新目录>` 在有 makepkg 的环境导出 AUR 文件；不覆盖现有目录，也不推送。已有 AUR 包先与维护者协作。

[静态 CI](.github/workflows/check.yml) 与[双架构构建 CI](.github/workflows/build.yml)随仓库提供；首次推送后才能产生远端结果。构建 CI 复用固定提交的 Omarchy 官方构建工具，只保留日志，不上传专有软件包。

## 仓库结构

```text
omarchy-tools              显眼的统一入口：面板、软件安装、更新与卸载
catalog.json               软件、来源、维护归属、验证状态
pkgbuilds/<pkgbase>/        独立 PKGBUILD、.SRCINFO、辅助文件、包说明
  .omarchy/package.json    Omarchy 上游更新配置，候选阶段手动 hold
plugins/catalog.json       公开插件目录、部署白名单与验证状态
plugins/<name>/            独立 manifest、QML/Python、许可证与插件测试
tools/                     软件包/插件检查、更新发现、导出与 CI 辅助
tests/                     工具行为测试，不模拟软件运行成功
docs/                      调研、打包、测试、发布及软件适配记录
```

新增软件先查 Arch、AUR、Omarchy。已有合适的软件包时只增加目录项和适配记录；确需新增或改进时才维护本地配方。向 Omarchy 导入后以其维护流程为准，不能假定它会自动同步这里或 AUR 的更改。

## 文档

- [调研结论与分发选择](docs/research.md)
- [编写和维护配方](docs/packaging.md)
- [测试与证据要求](docs/testing.md)
- [首次落地验证记录](docs/validation.md)
- [Quickshell 插件组织、部署与分发](plugins/README.md)
- [Agent Entry 迁移验证记录](docs/plugins-validation.md)
- [AUR、Omarchy 与自建源发布流程](docs/publishing.md)
- [钉钉官方 Arch 支持及现成 Omarchy 配方](docs/software/dingtalk.md)

本仓库原创代码与说明采用 [0BSD](LICENSE)。迁入的 [Agent Entry](plugins/agent-entry/LICENSE) 保留 Apache-2.0，其他子目录有独立声明时以其为准。Qoder 等第三方程序保留其各自许可证；候选配方不代表获得了二进制再分发授权，也不代表 Qoder、钉钉或 Omarchy 官方背书。
